#!/usr/bin/env python3
"""
M3U8下载工具主入口
使用Scrapy框架下载M3U8文件中的视频片段
"""

from __future__ import annotations

import argparse
import sys

from constants import DEFAULT_BASE_DIR, DEFAULT_CONCURRENT, DEFAULT_DELAY, LOGS_DIR
from utils.logger import get_logger
from utils.scrapy_manager import DownloadConfig, run_scrapy

# 初始化 logger
logger = get_logger(__name__)


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
    run_scrapy(config)
    _print_footer(config)


if __name__ == "__main__":
    main()
