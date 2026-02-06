# 自定义 LogFormatter：根据 spider.log_pipeline_items 决定是否输出 pipeline 产出的 item 日志

from __future__ import annotations

from typing import Any, Union

from scrapy import Spider
from scrapy.logformatter import LogFormatter
from twisted.python.failure import Failure

from scrapy.http import Response


class M3U8LogFormatter(LogFormatter):
    """
    当 spider 设置 log_pipeline_items=False 时，不打印「Scraped from ... + item」这类
    pipeline 相关的 DEBUG 日志，避免日志刷屏。
    """

    def scraped(
        self,
        item: Any,
        response: Union[Response, Failure, None],
        spider: Spider,
    ) -> dict | None:
        if not getattr(spider, "log_pipeline_items", False):
            return None
        return super().scraped(item, response, spider)
