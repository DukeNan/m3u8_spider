#!/usr/bin/env python3
"""
M3U8下载工具主入口
使用Scrapy框架下载M3U8文件中的视频片段
"""

from __future__ import annotations

import argparse
import logging
import os  # 仅用于 os.chdir（pathlib 无等价 API）
import sys
from dataclasses import dataclass
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 添加scrapy项目路径到sys.path
sys.path.insert(0, str(Path(__file__).parent / "scrapy_project"))

from m3u8_spider.spiders.m3u8_downloader import M3U8DownloaderSpider


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


class M3U8DownloadRunner:
    """
    负责执行 M3U8 下载（单一职责：驱动 Scrapy 完成下载）
    依赖配置对象，不直接依赖 CLI 或全局状态。
    """

    def __init__(self, config: DownloadConfig) -> None:
        self._config = config

    def run(self) -> None:
        """执行下载：切换工作目录、应用设置、启动爬虫、恢复目录。"""
        original_cwd = Path.cwd()
        try:
            self._chdir_to_scrapy_project()
            self._start_crawler()
        finally:
            os.chdir(original_cwd)

    def _chdir_to_scrapy_project(self) -> None:
        """设置 Scrapy 项目路径并切换工作目录"""
        os.chdir(self._config.scrapy_project_dir)

    def _start_crawler(self) -> None:
        """获取 Scrapy 设置、更新参数、创建进程并启动爬虫"""
        self._config.download_dir.parent.mkdir(parents=True, exist_ok=True)

        log_dir = self._config.project_root / LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{self._config.sanitized_filename}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        )
        scrapy_logger = logging.getLogger("scrapy")
        scrapy_logger.addHandler(file_handler)

        settings = get_project_settings()
        settings.set("CONCURRENT_REQUESTS", self._config.concurrent)
        settings.set("DOWNLOAD_DELAY", self._config.delay)

        process = CrawlerProcess(settings)
        process.crawl(
            M3U8DownloaderSpider,
            m3u8_url=self._config.m3u8_url,
            filename=self._config.sanitized_filename,
            download_directory=str(self._config.download_dir),
            retry_urls=self._config.retry_urls,
        )
        process.start()


class DownloadApp:
    """
    高层入口：解析命令行、验证、打印信息、调用 M3U8DownloadRunner。
    不关心 Scrapy 内部实现，只依赖 DownloadConfig 和 Runner。
    """

    def __init__(self, argv: list[str] | None = None) -> None:
        self._argv = argv if argv is not None else sys.argv[1:]

    def run(self) -> None:
        """解析参数 → 构建配置 → 打印摘要 → 执行下载 → 打印后续步骤"""
        config = self._parse_and_validate_args()
        self._print_header(config)
        print("开始下载...\n")
        M3U8DownloadRunner(config).run()
        self._print_footer(config)

    def _parse_and_validate_args(self) -> DownloadConfig:
        """解析 CLI 并返回有效的 DownloadConfig（无效时退出进程）"""
        parser = self._build_parser()
        args = parser.parse_args(self._argv)

        try:
            return DownloadConfig(
                m3u8_url=args.m3u8_url,
                filename=args.filename,
                concurrent=args.concurrent,
                delay=args.delay,
            )
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)

    def _build_parser(self) -> argparse.ArgumentParser:
        """构建 argparse 解析器"""
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
        return parser

    def _print_header(self, config: DownloadConfig) -> None:
        """打印下载前的摘要信息"""
        sep = "=" * 60
        print(f"\n{sep}")
        print("M3U8下载工具")
        print(sep)
        print(f"M3U8 URL: {config.m3u8_url}")
        print(f"保存目录: {DEFAULT_BASE_DIR}/{config.sanitized_filename}")
        print(f"日志文件: {LOGS_DIR}/{config.sanitized_filename}.log")
        print(f"并发数: {config.concurrent}")
        print(f"下载延迟: {config.delay}秒")
        print(f"{sep}\n")

    def _print_footer(self, config: DownloadConfig) -> None:
        """打印下载完成提示与下一步操作"""
        sep = "=" * 60
        name = config.sanitized_filename
        print(f"\n{sep}")
        print("✅ 下载完成!")
        print(f"文件保存在: {config.download_dir}")
        print(f"{sep}\n")
        print("下一步操作:")
        print(f"  校验下载: python validate_downloads.py {name}")
        print(f"  合并为MP4: python merge_to_mp4.py {name}")


def main() -> None:
    """主函数：委托给 DownloadApp"""
    DownloadApp().run()


if __name__ == "__main__":
    main()
