#!/usr/bin/env python3
"""
从页面 HTML 中抓取 M3U8 URL 的模块
供 M3U8 刷新守护进程使用，依赖可选：crawl4ai（pip install crawl4ai）
"""

from __future__ import annotations

import asyncio
import re


def find_m3u8_url(html: str) -> str | None:
    """
    从 HTML 中用正则提取 M3U8 URL。

    Args:
        html: 页面 HTML 内容

    Returns:
        第一个匹配的 M3U8 URL，无匹配返回 None
    """
    pattern = r'src=.*?(https?:\/\/[^\s\'"]+\.m3u8(?:\?[^\s\'"]*)?|\/[^\s\'"]+\.m3u8(?:\?[^\s\'"]*)?)'
    matches = re.findall(pattern, html)
    return matches[0] if matches else None


def fetch_m3u8_from_page(page_url: str) -> str | None:
    """
    使用 crawl4ai 访问页面并解析出 M3U8 URL（同步接口，内部用 asyncio.run 调用异步爬虫）。

    Args:
        page_url: 视频详情页 URL（如 https://jable.tv/videos/xxx/）

    Returns:
        解析到的 M3U8 URL，失败或未找到返回 None

    Raises:
        ImportError: 未安装 crawl4ai 时提示安装
    """
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig
    except ImportError as e:
        raise ImportError(
            "M3U8 刷新功能需要 crawl4ai。请安装: pip install crawl4ai，并执行 playwright install"
        ) from e

    async def _fetch() -> str | None:
        async with AsyncWebCrawler(
            config=BrowserConfig(
                viewport_height=800,
                viewport_width=1200,
                headless=True,
                verbose=False,
            )
        ) as crawler:
            results = await crawler.arun(url=page_url)
            if results and results[0].success and results[0].html:
                return find_m3u8_url(results[0].html)
        return None

    return asyncio.run(_fetch())
