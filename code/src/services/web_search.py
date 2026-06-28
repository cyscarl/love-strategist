"""联网搜索服务 —— 使用 DuckDuckGo 免费搜索。

无需 API Key，用于为智能体提供实时信息。
"""

import requests
from loguru import logger


def search_web(query: str, max_results: int = 3) -> str:
    """搜索网页并返回摘要文本。

    Args:
        query: 搜索关键词
        max_results: 最多返回条数

    Returns:
        搜索结果摘要文本，失败返回空字符串
    """
    try:
        # DuckDuckGo Instant Answer API（免费，无需 Key）
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return ""

        data = resp.json()
        parts = []

        # 摘要
        abstract = data.get("AbstractText", "")
        if abstract:
            parts.append(abstract)

        # 相关话题
        related = data.get("RelatedTopics", [])
        for topic in related[:max_results]:
            text = topic.get("Text", "")
            if text:
                parts.append(text)

        result = "\n".join(parts[:max_results + 1])
        if result:
            logger.info(f"搜索 '{query}': {len(result)} 字符")
        return result[:800]  # 限制长度
    except Exception as e:
        logger.debug(f"搜索失败: {e}")
        return ""


def detect_hot_topics(messages: list[str]) -> str:
    """检测对话中是否涉及需要联网搜索的热点话题。

    返回检测到的关键词，用于搜索。
    """
    import re
    text = " ".join(messages[-10:])  # 最近10条消息

    # 热点信号词
    hot_signals = [
        "热搜", "最近", "网上", "新闻", "听说", "火", "热点",
        "梗", "刷到", "抖音", "微博", "小红书", "B站",
        "电影", "新歌", "综艺", "游戏", "比赛",
        "最近很火", "你看了吗", "你知道吗",
    ]

    found = []
    for signal in hot_signals:
        if signal in text:
            found.append(signal)

    if found:
        # 尝试提取具体话题
        # 简单策略：取信号词前后各15个字作为搜索上下文
        for s in found[:2]:
            idx = text.find(s)
            start = max(0, idx - 15)
            end = min(len(text), idx + len(s) + 15)
            context = text[start:end].strip()
            return context

    return ""
