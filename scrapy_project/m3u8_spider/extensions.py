# 扩展：根据 M3U8_LOG_FILE 为 root logger 添加文件 Handler，实现控制台+文件双输出

from __future__ import annotations

import logging

from scrapy.crawler import Crawler


class M3U8FileLogExtension:
    """
    当 settings 中设置 M3U8_LOG_FILE 时，向 root logger 添加 FileHandler，
    与 Scrapy 的 StreamHandler 并存，实现控制台+文件双输出。
    在 from_crawler 时添加，与 process.start() 前添加等效，确保整次 run 的日志都落文件。
    """

    def __init__(self, log_file: str | None, crawler: Crawler):
        self._log_file = log_file
        self._crawler = crawler
        self._handler: logging.FileHandler | None = None

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> "M3U8FileLogExtension":
        log_file = crawler.settings.get("M3U8_LOG_FILE")
        ext = cls(log_file, crawler)
        if log_file:
            ext._add_file_handler()
        return ext

    def _add_file_handler(self) -> None:
        if not self._log_file or self._handler is not None:
            return
        settings = self._crawler.settings
        self._handler = logging.FileHandler(
            self._log_file,
            mode="a",
            encoding=settings.get("LOG_ENCODING", "utf-8"),
        )
        self._handler.setFormatter(
            logging.Formatter(
                fmt=settings.get("LOG_FORMAT"),
                datefmt=settings.get("LOG_DATEFORMAT"),
            )
        )
        self._handler.setLevel(settings.get("LOG_LEVEL", "DEBUG"))
        logging.root.addHandler(self._handler)
