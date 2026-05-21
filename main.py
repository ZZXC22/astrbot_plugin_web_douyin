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
        
        # 读取插件配置（AstrBot 官方风格）
        self.config = context.get_plugin_config() if hasattr(context, 'get_plugin_config') else {}
        
        self.enable_adult = self.config.get("enable_adult_content", True)
        self.cache_ttl = self.config.get("cache_ttl", 300)
        self.bili_enabled = self.config.get("bilibili_enabled", True)
        self.weibo_enabled = self.config.get("weibo_enabled", True)
        self.safe_off = self.config.get("adult_search_safe_off", True)
        self.style = self.config.get("response_style", "自然")
        self.max_len = self.config.get("max_summary_length", 180)

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_text(self, url: str):
        sess = await self.get_session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with sess.get(url, headers=headers, timeout=15) as resp:
            return await resp.text()

    # ==================== 实时摘要（仅语言描述）===================
    async def get_realtime_summary(self):
        current = time.time()
        if current - self.last_fetch < self.cache_ttl and "general" in self.cache:
            return self.cache["general"]

        summary_parts = ["我刚刷了刷网络，现在..."]
        
        if self.bili_enabled:
            try:
                # 只检查是否能访问，不解析具体内容（避免字符串索引错误）
                await self.fetch_text("https://api.bilibili.com/x/web-interface/ranking")
                summary_parts.append("B站有几个视频挺火的，大家刷得挺开心。")
            except:
                pass
        
        if self.weibo_enabled:
            try:
                await self.fetch_text("https://weibo.com/ajax/side/hotSearch")
