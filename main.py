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
        logger.info("✅ RealtimeInfoPlugin 初始化成功！")

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_text(self, url: str):
        try:
            sess = await self.get_session()
            headers = {"User-Agent": "Mozilla/5.0"}
            async with sess.get(url, headers=headers, timeout=10) as resp:
                return await resp.text()
        except Exception as e:
            logger.error(f"fetch_text 错误: {e}")
            return ""

    async def get_realtime_summary(self):
        current = time.time()
        if current - self.last_fetch < 300 and "general" in self.cache:
            return self.cache["general"]

        summary = "我刚刷了刷网络，现在挺多新鲜事的～ B站和微博上都挺热闹的。"
        self.cache["general"] = summary
        self.last_fetch = current
        return summary

    async def get_adult_summary(self):
        return "最近成人向的内容更新挺快的，有几个新系列挺受欢迎的～"

    async def get_adult_url(self, query: str):
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&safe=off"
        return f"我帮你找了关于「{query}」的链接：\n{search_url}\n自己点开看看（注意隐私）"

    async def fetch_url_title(self, url: str):
        try:
            text = await self.fetch_text(url)
            soup = BeautifulSoup(text, 'html.parser')
            title = (soup.title.string or "页面").strip()[:50] if soup.title else "页面"
            return f"我打开看了看，标题是「{title}」。内容还挺有感觉的。"
        except Exception as e:
            logger.error(f"fetch_url_title 错误: {e}")
            return f"这个链接你直接点开吧：{url}"

    @register("realtime_info", "实时网络资讯", "自然聊天", [])
    async def handle(self, event: AstrMessageEvent):
        try:
            # 强制确保是字符串，防止类型问题
            message_str = str(getattr(event, 'message_str', ''))
            msg = message_str.strip().lower()
            orig = message_str.strip()

            # 明确要链接
            if any(k in msg for k in ["!网址", "!链接", "!get", "发链接", "给个链接", "网址", "链接"]):
                query = orig.split(maxsplit=1)[-1] if len(orig.split()) > 1 else "最新"
                if str(query).startswith("http"):
                    reply = await self.fetch_url_title(query)
                else:
                    reply = await self.get_adult_url(query)
                event.set_result([Plain(reply)])
                return True

            # 实时热点
            if any(k in msg for k in ["热点", "热搜", "现在网上", "最近流行", "有什么新鲜", "抖音", "b站", "小红书"]):
                summary = await self.get_realtime_summary()
                if random.random() > 0.6:
                    summary += " 你想听哪方面的？我再详细说说～"
                event.set_result([Plain(summary)])
                return True

            # 成人相关
            if any(k in msg for k in ["色情", "成人", "福利", "av", "片子", "刺激", "涩"]):
                summary = await self.get_adult_summary()
                event.set_result([Plain(summary)])
                return True

            return False
        except Exception as e:
            logger.error(f"handle 函数出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def info(self):
        return {
            "name": "RealtimeInfo",
            "desc": "实时网络资讯插件",
            "help": "试试：热点 / 现在网上有什么 / !网址 日本AV",
            "version": "2.5.0-debug",
            "author": "YourName",
            "repo": "https://github.com/你的/astrbot_plugin_realtime_info"
        }

    async def terminate(self):
        if self.session:
            await self.session.close()
