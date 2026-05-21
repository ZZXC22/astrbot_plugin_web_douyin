import random
from astrbot.core import logger
from astrbot import filter as astrbot_filter
from astrbot.core.star import Context, Star
from astrbot.core.message.message_event_result import MessageEventResult, MessageChain
import httpx

class WebDouyinPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # ==================== 命令 ====================
    @astrbot_filter.command("搜索", alias=["查", "搜"])
    async def web_search(self, event, query: str):
        """联网搜索：搜索 关键词"""
        if not query:
            return event.plain_result("请输入搜索关键词，例如：搜索 今天天气")
        
        result = await self._do_web_search(query)
        return event.plain_result(f"🔍 搜索「{query}」结果：\n{result}")

    @astrbot_filter.command("抖音热搜")
    async def douyin_hot(self, event):
        """抖音实时热搜"""
        hot_list = await self._get_douyin_hot()
        if not hot_list:
            return event.plain_result("获取抖音热搜失败，请稍后重试。")
        
        msg = "🔥 抖音实时热搜 Top 10：\n"
        for i, item in enumerate(hot_list[:10], 1):
            title = item.get('title', 'N/A')
            hot = item.get('hot', item.get('view_count', 'N/A'))
            msg += f"{i}. {title} ({hot})\n"
        return event.plain_result(msg)

    @astrbot_filter.command("抖音热门")
    async def douyin_popular(self, event):
        """抖音热门视频推荐"""
        videos = await self._get_douyin_popular()
        if not videos:
            return event.plain_result("获取热门视频失败，请稍后重试。")
        
        video = random.choice(videos[:15])
        title = video.get('title', '未知标题')
        share_url = video.get('share_url', video.get('url', ''))
        desc = video.get('desc', '')[:120]
        
        chain = MessageChain().text(f"🎥 抖音热门推荐：\n【{title}】\n{desc}\n🔗 {share_url}")
        if video.get('cover'):
            chain.image(video['cover'])
        return event.set_result(chain)

    # ==================== 实现 ====================
    async def _do_web_search(self, query: str) -> str:
        """联网搜索（DuckDuckGo）"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
                )
                data = resp.json()
                abstract = data.get("AbstractText") or "未找到详细结果，可尝试其他关键词。"
                return abstract[:400]
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return "搜索出错，请稍后重试。"

    async def _get_douyin_hot(self):
        """抖音热搜"""
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                # 免费公开接口（可替换更稳定源）
                resp = await client.get("https://v.api.aa1.cn/api/douyin/hot.php")
                data = resp.json()
                return data.get("data", [])[:20]
        except:
            # 备用数据
            return [{"title": "当前热搜接口维护中", "hot": "请稍后再试"}]

    async def _get_douyin_popular(self):
        """抖音热门视频"""
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get("https://v.api.aa1.cn/api/douyin/hot.php")
                data = resp.json()
                return data.get("data", [])
        except:
            return [{"title": "热门视频加载中...", "share_url": "https://douyin.com", "cover": None, "desc": "请稍后重试"}]
