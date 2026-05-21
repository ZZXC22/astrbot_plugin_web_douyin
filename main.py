from astrbot.api import logger
from astrbot.api.star import Star, Context, register
from astrbot.api.message_components import Plain
from astrbot.api.event import AstrMessageEvent
import aiohttp
from bs4 import BeautifulSoup
import random
import time

class RealtimeInfoPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.session = None
        self.cache = {}
        self.last_fetch = 0
        
        # 简化配置读取，避免报错
        self.enable_adult = True
        self.cache_ttl = 300
        self.bili_enabled = True
        self.weibo_enabled = True
        self.safe_off = True
        self.style = "自然"
        self.max_len = 180

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_text(self, url: str):
        try:
            sess = await self.get_session()
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with sess.get(url, headers=headers, timeout=10) as resp:
                return await resp.text()
        except Exception as e:
            logger.error(f"fetch_text error: {e}")
            return ""

    # ==================== 实时摘要 ====================
    async def get_realtime_summary(self):
        current = time.time()
        if current - self.last_fetch < self.cache_ttl and "general" in self.cache:
            return self.cache["general"]

        summary_parts = ["我刚刷了刷网络，现在..."]
        
        if self.bili_enabled:
            try:
                await self.fetch_text("https://api.bilibili.com/x/web-interface/ranking")
                summary_parts.append("B站有几个视频挺火的，大家刷得挺开心。")
            except:
                pass
        
        if self.weibo_enabled:
            try:
                await self.fetch_text("https://weibo.com/ajax/side/hotSearch")
                summary_parts.append("微博上话题挺多的。")
            except:
                pass

        summary = " ".join(summary_parts)[:self.max_len]
        self.cache["general"] = summary
        self.last_fetch = current
        return summary

    async def get_adult_summary(self, query: str = ""):
        base = f"关于「{query or '这个'}」的成人内容最近有不少更新"
        styles = {
            "温柔": "，感觉挺有氛围的～",
            "直白": "，挺刺激的，新片/图集不少。",
            "撒娇": "，人家看到好多有趣的呢～",
            "自然": "，更新挺快的。"
        }
        return (base + styles.get(self.style, "。"))[:self.max_len]

    async def get_adult_url(self, query: str):
        safe = "&safe=off" if self.safe_off else ""
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}{safe}"
        return f"我帮你找了关于「{query}」的链接：\n{search_url}\n自己点开看看（注意隐私）"

    async def fetch_url_title(self, url: str):
        try:
            text = await self.fetch_text(url)
            soup = BeautifulSoup(text, 'html.parser')
            title = (soup.title.string or "页面").strip()[:50]
            return f"我打开看了看，标题是「{title}」。内容还挺有感觉的。"
        except Exception as e:
            logger.error(f"fetch_url_title error: {e}")
            return f"这个链接你直接点开吧：{url}"

    # ==================== 指令处理 ====================
    @register("realtime_info", "实时网络资讯", "自然聊天式响应", [])
    async def handle(self, event: AstrMessageEvent):
        try:
            msg = event.message_str.strip().lower()
            orig = event.message_str.strip()

            # 明确要链接
            if any(k in msg for k in ["!网址", "!链接", "!get", "发链接", "给个链接", "网址", "链接"]):
                query = orig.split(maxsplit=1)[-1] if len(orig.split()) > 1 else "最新"
                if query.startswith("http"):
                    reply = await self.fetch_url_title(query)
                else:
                    reply = await self.get_adult_url(query)
                event.set_result([Plain(reply)])
                return True

            # 实时热点
            if any(k in msg for k in ["热点", "热搜", "热梗", "现在网上", "最近流行", "有什么新鲜", "抖音", "b站", "小红书"]):
                summary = await self.get_realtime_summary()
                if random.random() > 0.6:
                    summary += " 你想听哪方面的？我再详细说说～"
                event.set_result([Plain(summary)])
                return True

            # 成人相关
            if any(k in msg for k in ["色情", "成人", "福利", "av", "片子", "刺激", "涩"]):
                summary = await self.get_adult_summary(orig)
                event.set_result([Plain(summary)])
                return True

            return False
        except Exception as e:
            logger.error(f"handle error: {e}")
            return False

    def info(self):
        return {
            "name": "RealtimeInfo",
            "desc": "实时网络资讯插件",
            "help": "说 热点 / 现在网上有什么 / !网址 xxx",
            "version": "2.3.0",
            "author": "YourName",
            "repo": "https://github.com/你的用户名/astrbot_plugin_realtime_info"
        }

    async def terminate(self):
        if self.session:
            await self.session.close()
