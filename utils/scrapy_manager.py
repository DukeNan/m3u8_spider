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

    注意：
    - 如果提供 runner，则使用 CrawlerRunner 在已运行的 reactor 中运行爬虫
    - 如果未提供 runner，则使用 CrawlerProcess 创建新的 reactor（单次下载场景）
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

        # 使用 CrawlerProcess（单次下载场景）
        # 创建新的 reactor 并运行
        process = CrawlerProcess(settings, install_root_handler=False)
        process.crawl(
            M3U8DownloaderSpider,
            m3u8_url=config.m3u8_url,
            filename=config.sanitized_filename,
            download_directory=str(config.download_dir),
            retry_urls=config.retry_urls,
        )
        # 使用 start() 方法，它会阻塞直到所有爬虫和下载完成
        # stop_after_crawl=True (默认值) 确保等待所有请求（包括 pipeline 中的下载请求）完成
        # 这包括等待所有文件下载完成，而不仅仅是 spider 的 yield 完成
        process.start(stop_after_crawl=True)
    finally:
        os.chdir(original_cwd)


def run_scrapy_subprocess(config: DownloadConfig) -> None:
    """
    使用子进程运行 Scrapy（用于多次调用场景，如 auto_downloader）

    Args:
        config: 下载配置

    注意：
    - 每次下载都在独立的子进程中运行，避免 reactor 重启问题
    - 子进程会调用 main.py 来执行下载
    """
    import subprocess

    # 构建 main.py 的命令行参数
    main_py = config.project_root / "main.py"
    cmd = [
        sys.executable,
        str(main_py),
        config.m3u8_url,
        config.sanitized_filename,
        "--concurrent",
        str(config.concurrent),
        "--delay",
        str(config.delay),
    ]

    logger.info(f"启动子进程下载: {' '.join(cmd)}")

    # 运行子进程并等待完成
    result = subprocess.run(
        cmd,
        cwd=str(config.project_root),
        capture_output=False,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"子进程下载失败，返回码: {result.returncode}")
