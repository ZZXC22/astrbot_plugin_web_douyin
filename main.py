from astrbot.api.star import Star, Context
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain
from astrbot.api import logger
import aiohttp
import time
import json


class RealtimeInfoPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.session = None
        self.cache_text = ""
        self.cache_time = 0

        cfg = {}
        try:
            if hasattr(context, "get_plugin_config"):
                tmp = context.get_plugin_config()
                if isinstance(tmp, dict):
                    cfg = tmp
            elif hasattr(context, "get_config"):
                tmp = context.get_config()
                if isinstance(tmp, dict):
                    cfg = tmp
        except Exception as e:
            logger.warning(f"读取配置失败，使用默认值: {e}")

        self.enable_realtime = cfg.get("enable_realtime", True)
        self.cache_ttl_sec = int(cfg.get("cache_ttl_sec", 300))

        self.enable_bilibili = cfg.get("enable_bilibili", True)
        self.enable_weibo = cfg.get("enable_weibo", True)
        self.enable_douyin = cfg.get("enable_douyin", True)
        self.enable_xiaohongshu = cfg.get("enable_xiaohongshu", True)

        self.douyin_api_url = (cfg.get("douyin_api_url", "") or "").strip()
        self.xhs_api_url = (cfg.get("xiaohongshu_api_url", "") or "").strip()

        self.reply_style = cfg.get("reply_style", "自然")
        self.allow_link_on_explicit_request = cfg.get("allow_link_on_explicit_request", True)

        logger.info("RealtimeInfoPlugin loaded ✅")

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_text(self, url: str) -> str:
        try:
            sess = await self.get_session()
            headers = {"User-Agent": "Mozilla/5.0"}
            async with sess.get(url, headers=headers, timeout=10) as resp:
                return await resp.text()
        except Exception as e:
            logger.warning(f"fetch_text失败: {url} | {e}")
            return ""

    async def fetch_json(self, url: str):
        txt = await self.fetch_text(url)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None

    def style_wrap(self, text: str) -> str:
        if self.reply_style == "简洁":
            return text[:90]
        if self.reply_style == "活泼":
            return text + " 😄"
        return text

    def pick_titles_from_common_schema(self, data, max_n=3):
        """
        兼容常见返回结构：
        - {"data":[{"title":"..."}, ...]}
        - {"items":[{"name":"..."}, ...]}
        - [{"title":"..."}, ...]
        """
        titles = []

        if isinstance(data, dict):
            for key in ["data", "items", "list", "result"]:
                v = data.get(key)
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            t = item.get("title") or item.get("name") or item.get("word")
                            if isinstance(t, str) and t.strip():
                                titles.append(t.strip())
                    break
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    t = item.get("title") or item.get("name") or item.get("word")
                    if isinstance(t, str) and t.strip():
                        titles.append(t.strip())

        return titles[:max_n]

    async def get_realtime_summary(self) -> str:
        if not self.enable_realtime:
            return self.style_wrap("我先按本地信息聊聊，实时联网暂时没开。")

        now = time.time()
        if now - self.cache_time < self.cache_ttl_sec and self.cache_text:
            return self.cache_text

        parts = ["我刚看了下，网上现在挺热闹的。"]

        # B站可用性探测
        if self.enable_bilibili:
            txt = await self.fetch_text("https://api.bilibili.com/x/web-interface/ranking")
            if txt:
                parts.append("B站有几条视频讨论度很高。")

        # 微博可用性探测
        if self.enable_weibo:
            txt = await self.fetch_text("https://weibo.com/ajax/side/hotSearch")
            if txt:
                parts.append("微博也有不少新话题在发酵。")

        # 抖音：优先使用你配置的API
        if self.enable_douyin and self.douyin_api_url:
            data = await self.fetch_json(self.douyin_api_url)
            if data is not None:
                titles = self.pick_titles_from_common_schema(data)
                if titles:
                    parts.append("抖音这会儿在聊：" + "、".join(titles) + "。")
                else:
                    parts.append("抖音热榜有更新。")

        # 小红书：优先使用你配置的API
        if self.enable_xiaohongshu and self.xhs_api_url:
            data = await self.fetch_json(self.xhs_api_url)
            if data is not None:
                titles = self.pick_titles_from_common_schema(data)
                if titles:
                    parts.append("小红书最近热议：" + "、".join(titles) + "。")
                else:
                    parts.append("小红书热门内容在更新。")

        summary = self.style_wrap(" ".join(parts))
        self.cache_text = summary
        self.cache_time = now
        return summary

    async def build_search_link(self, query: str) -> str:
        q = (query or "实时热点").strip()
        url = f"https://www.google.com/search?q={q.replace(' ', '+')}"
        return self.style_wrap(f"你要的链接我找到了：{url}")

    async def on_message(self, event: AstrMessageEvent):
        try:
            text = str(getattr(event, "message_str", "")).strip()
            lower = text.lower()

            if any(k in lower for k in ["热点", "热搜", "现在网上", "最近有什么", "新鲜事", "热梗", "抖音", "小红书"]):
                reply = await self.get_realtime_summary()
                event.set_result([Plain(reply)])
                return True

            if self.allow_link_on_explicit_request and any(k in lower for k in ["链接", "网址", "!网址", "!链接", "!get", "发个链接"]):
                parts = text.split(maxsplit=1)
                query = parts[1] if len(parts) > 1 else "实时热点"
                reply = await self.build_search_link(query)
                event.set_result([Plain(reply)])
                return True

            return False
        except Exception as e:
            logger.error(f"on_message error: {e}")
            return False

    async def terminate(self):
        if self.session:
            await self.session.close()
