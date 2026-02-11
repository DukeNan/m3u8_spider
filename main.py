#!/usr/bin/env python3
"""
M3U8下载工具主入口
使用Scrapy框架下载M3U8文件中的视频片段
"""

from __future__ import annotations

import argparse
import os  # 仅用于 os.chdir（pathlib 无等价 API）
import sys
from dataclasses import dataclass
from pathlib import Path

from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor

# 添加scrapy项目路径到sys.path
sys.path.insert(0, str(Path(__file__).parent / "scrapy_project"))

from m3u8_spider.spiders.m3u8_downloader import M3U8DownloaderSpider
from logger_config import get_logger

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 常量 / 配置
# ---------------------------------------------------------------------------

# 文件名中不允许的字符
INVALID_FILENAME_CHARS: str = '<>:"/\\|?*'

# 默认并发数与延迟
DEFAULT_CONCURRENT: int = 32
DEFAULT_DELAY: float = 0.0

# 默认下载输出基目录（项目根下的 movies/）
DEFAULT_BASE_DIR: str = "movies"

# 日志目录（项目根下的 logs/）
LOGS_DIR: str = "logs"


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
        """项目根目录（main.py 所在目录）"""
        return Path(__file__).resolve().parent

    @property
    def scrapy_project_dir(self) -> Path:
        """Scrapy 项目目录"""
        return self.project_root / "scrapy_project"

    @property
    def download_dir(self) -> Path:
        """下载输出目录路径（默认在 movies/ 下）"""
        return self.project_root / DEFAULT_BASE_DIR / self.sanitized_filename


def _parse_args(argv: list[str] | None = None) -> DownloadConfig:
    """解析 CLI 并返回有效的 DownloadConfig，无效时退出进程。"""
    parser = argparse.ArgumentParser(
        description="M3U8文件下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py https://example.com/playlist.m3u8 my_video
  python main.py https://example.com/playlist.m3u8 video_name --concurrent 16
        """,
    )
    parser.add_argument("m3u8_url", help="M3U8文件的URL地址")
    parser.add_argument(
        "filename",
        help="保存的文件名（将在默认 movies/ 目录下创建同名子目录）",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT,
        help=f"并发下载数（默认: {DEFAULT_CONCURRENT}）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"下载延迟（秒，默认: {DEFAULT_DELAY}）",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return DownloadConfig(
            m3u8_url=args.m3u8_url,
            filename=args.filename,
            concurrent=args.concurrent,
            delay=args.delay,
        )
    except ValueError as e:
        logger.error(f"错误: {e}")
        sys.exit(1)


def _run_scrapy(config: DownloadConfig, runner: CrawlerRunner | None = None) -> None:
    """
    运行 Scrapy：chdir、注入本 run 参数、启动爬虫、恢复 cwd。

    Args:
        config: 下载配置
        runner: 可选的 CrawlerRunner 实例（用于多次调用场景，如 auto_downloader）
                如果提供，将使用此 runner；否则创建新的 CrawlerProcess
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

        if runner is not None:
            # 使用提供的 runner（用于多次调用场景）
            # 确保在 reactor 线程中执行
            import threading
            from twisted.internet import reactor as twisted_reactor

            event = threading.Event()
            exception_holder = [None]
            deferred_holder = [None]

            def run_crawl():
                """在 reactor 线程中执行爬虫"""
                try:
                    deferred = runner.crawl(
                        M3U8DownloaderSpider,
                        m3u8_url=config.m3u8_url,
                        filename=config.sanitized_filename,
                        download_directory=str(config.download_dir),
                        retry_urls=config.retry_urls,
                    )
                    deferred_holder[0] = deferred

                    def callback(_):
                        event.set()

                    def errback(failure):
                        exception_holder[0] = failure
                        event.set()

                    deferred.addCallbacks(callback, errback)
                except Exception as e:
                    exception_holder[0] = e
                    event.set()

            # 在 reactor 线程中执行
            if twisted_reactor.running:  # type: ignore[attr-defined]
                twisted_reactor.callFromThread(run_crawl)  # type: ignore[attr-defined]
            else:
                # 如果 reactor 未运行，直接执行（不应该发生）
                run_crawl()

            # 等待 deferred 完成（阻塞）
            event.wait()

            if exception_holder[0]:
                if hasattr(exception_holder[0], 'value'):
                    raise exception_holder[0].value
                else:
                    raise exception_holder[0]
        else:
            # 首次运行，使用 CrawlerProcess
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


def _print_header(config: DownloadConfig) -> None:
    """打印下载前的摘要信息。"""
    sep = "=" * 60
    logger.info(f"\n{sep}")
    logger.info("M3U8下载工具")
    logger.info(sep)
    logger.info(f"M3U8 URL: {config.m3u8_url}")
    logger.info(f"保存目录: {DEFAULT_BASE_DIR}/{config.sanitized_filename}")
    logger.info(f"日志文件: {LOGS_DIR}/{config.sanitized_filename}.log")
    logger.info(f"并发数: {config.concurrent}")
    logger.info(f"下载延迟: {config.delay}秒")
    logger.info(f"{sep}\n")


def _print_footer(config: DownloadConfig) -> None:
    """打印下载完成提示与下一步操作。"""
    sep = "=" * 60
    name = config.sanitized_filename
    logger.info(f"\n{sep}")
    logger.info("✅ 下载完成!")
    logger.info(f"文件保存在: {config.download_dir}")
    logger.info(f"{sep}\n")
    logger.info("下一步操作:")
    logger.info(f"  校验下载: python validate_downloads.py {name}")
    logger.info(f"  合并为MP4: python merge_to_mp4.py {name}")


def main() -> None:
    """主入口：解析参数 → 打印摘要 → 运行 Scrapy → 打印后续步骤。"""
    config = _parse_args()
    _print_header(config)
    logger.info("开始下载...\n")
    _run_scrapy(config)
    _print_footer(config)


if __name__ == "__main__":
    main()
