#!/usr/bin/env python3
"""
Scrapy 管理模块
负责 Scrapy 爬虫的配置和运行
"""

from __future__ import annotations

import os  # 仅用于 os.chdir（pathlib 无等价 API）
import sys
from dataclasses import dataclass
from pathlib import Path

from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.project import get_project_settings

from constants import (
    DEFAULT_BASE_DIR,
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    INVALID_FILENAME_CHARS,
    LOGS_DIR,
)

# 添加scrapy项目路径到sys.path
# 获取项目根目录（utils 的父目录）
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "scrapy_project"))

# 必须在 sys.path 修改后才能导入这些模块
from m3u8_spider.spiders.m3u8_downloader import M3U8DownloaderSpider  # noqa: E402
from utils.logger import get_logger  # noqa: E402

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DownloadConfig:
    """M3U8 下载配置（不可变）"""

    m3u8_url: str
    filename: str
    concurrent: int = DEFAULT_CONCURRENT
    delay: float = DEFAULT_DELAY
    retry_urls: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.m3u8_url.startswith(("http://", "https://")):
            raise ValueError(f"无效的URL: {self.m3u8_url}")
        if not self.filename or not self.filename.strip():
            raise ValueError("文件名不能为空")

    @property
    def sanitized_filename(self) -> str:
        """清理后的文件名（移除不合法字符）"""
        name = self.filename.strip()
        for char in INVALID_FILENAME_CHARS:
            name = name.replace(char, "_")
        return name

    @property
    def project_root(self) -> Path:
        """项目根目录（utils 的父目录）"""
        return Path(__file__).resolve().parent.parent

    @property
    def scrapy_project_dir(self) -> Path:
        """Scrapy 项目目录"""
        return self.project_root / "scrapy_project"

    @property
    def download_dir(self) -> Path:
        """下载输出目录路径（默认在 movies/ 下）"""
        return self.project_root / DEFAULT_BASE_DIR / self.sanitized_filename


# ---------------------------------------------------------------------------
# Scrapy 运行函数
# ---------------------------------------------------------------------------


def run_scrapy(config: DownloadConfig, runner: CrawlerRunner | None = None) -> None:
    """
    运行 Scrapy：chdir、注入本 run 参数、启动爬虫、恢复 cwd。

    Args:
        config: 下载配置
        runner: 可选的 CrawlerRunner 实例（用于多次调用场景，如 auto_downloader）
                如果提供，将使用此 runner；否则创建新的 CrawlerProcess

    注意：由于 CrawlerRunner 在多线程环境下的复杂性，当前实现总是使用 CrawlerProcess
    来确保每次下载都是独立且可靠的。
    """
    original_cwd = Path.cwd()
    try:
        os.chdir(config.scrapy_project_dir)
        config.download_dir.parent.mkdir(parents=True, exist_ok=True)
        log_dir = config.project_root / LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{config.sanitized_filename}.log"

        settings = get_project_settings()
        settings.set("CONCURRENT_REQUESTS", config.concurrent)
        settings.set("DOWNLOAD_DELAY", config.delay)
        settings.set("M3U8_LOG_FILE", str(log_file))

        # 总是使用 CrawlerProcess 来确保每次下载都是独立的
        # 这样可以避免 CrawlerRunner 在多线程环境下的复杂性和潜在问题
        process = CrawlerProcess(settings)
        process.crawl(
            M3U8DownloaderSpider,
            m3u8_url=config.m3u8_url,
            filename=config.sanitized_filename,
            download_directory=str(config.download_dir),
            retry_urls=config.retry_urls,
        )
        process.start()
    finally:
        os.chdir(original_cwd)
