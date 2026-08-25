"""重试模式启动流程测试。"""

from __future__ import annotations

import asyncio

from scrapy.http import Request, TextResponse

from m3u8_spider.spiders.m3u8_downloader import M3U8DownloaderSpider


async def _collect_start_output(spider: M3U8DownloaderSpider) -> list:
    return [item async for item in spider.start()]


class TestRetryStart:
    """重试 Item 必须从 Request callback 产出。"""

    def test_yields_resolved_items_from_seed_callback(self, tmp_path) -> None:
        spider = M3U8DownloaderSpider(
            m3u8_url="https://example.com/hls/video/playlist.m3u8",
            filename="video",
            download_directory=str(tmp_path),
            retry_urls=[{"url": "segment-1.ts", "filename": "segment-1.ts"}],
        )

        requests = asyncio.run(_collect_start_output(spider))

        assert len(requests) == 1
        assert isinstance(requests[0], Request)
        assert requests[0].callback == spider._parse_retry_seed
        response = TextResponse(url=requests[0].url, request=requests[0])
        items = list(requests[0].callback(response))
        assert len(items) == 1
        assert items[0]["url"] == "https://example.com/hls/video/segment-1.ts"
        assert items[0]["filename"] == "segment-1.ts"
