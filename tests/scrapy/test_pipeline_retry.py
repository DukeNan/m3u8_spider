"""M3U8 文件 pipeline 的恢复重试测试。"""

from __future__ import annotations

from unittest.mock import patch

from scrapy import Request
from scrapy.pipelines.files import FilesPipeline

from m3u8_spider.pipelines import M3U8FilePipeline


class TestM3U8FilePipelineRetry:
    """校验失败的片段必须绕过 FilesPipeline 的 uptodate 缓存。"""

    def test_force_download_bypasses_parent_cache_check(self) -> None:
        pipeline = object.__new__(M3U8FilePipeline)
        request = Request("https://example.com/segment.ts", meta={"force_download": True})

        with patch.object(FilesPipeline, "media_to_download") as parent_method:
            result = pipeline.media_to_download(request, info=None)

        assert result is None
        parent_method.assert_not_called()

    def test_regular_download_uses_parent_cache_check(self) -> None:
        pipeline = object.__new__(M3U8FilePipeline)
        request = Request("https://example.com/segment.ts")

        with patch.object(FilesPipeline, "media_to_download", return_value="cached") as parent_method:
            result = pipeline.media_to_download(request, info=None)

        assert result == "cached"
        parent_method.assert_called_once_with(request, None, item=None)
