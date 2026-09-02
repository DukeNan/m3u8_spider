#!/usr/bin/env python3
"""
M3U8 地址提取工具入口
访问视频详情页并解析出 M3U8 URL，独立运行，不依赖数据库
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from m3u8_spider.core.m3u8_fetcher import fetch_m3u8_from_page
from m3u8_spider.logger import setup_logger

# 日志输出到 stderr，保证 stdout 仅含解析结果，便于管道使用
logger = setup_logger(name=__name__, stream=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析 CLI 参数。"""
    parser = argparse.ArgumentParser(
        description="M3U8 地址提取工具：访问详情页并解析出 M3U8 URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  m3u8-fetch https://example.com/videos/xxx/
  m3u8-fetch https://example.com/videos/xxx/ --output found.txt
  m3u8-fetch --file urls.txt --output found.txt

说明:
  - 结果 URL 输出到 stdout，进度与错误输出到 stderr，stdout 可直接管道使用
  - 批量文件为 UTF-8 文本，每行一个页面 URL，空行与 # 开头的注释行会被跳过
  - 需安装可选依赖: pip install crawl4ai && playwright install
        """,
    )
    parser.add_argument(
        "page_url",
        nargs="?",
        help="视频详情页 URL（与 --file 二选一）",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="批量模式：每行一个页面 URL 的 UTF-8 文本文件（与 page_url 二选一）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="可选：将解析到的 M3U8 URL 逐行写入该文件（覆盖写）",
    )
    return parser.parse_args(argv if argv is not None else sys.argv[1:])


def read_urls_from_file(path: Path) -> list[str]:
    """读取批量文件，返回页面 URL 列表（跳过空行与 # 注释行）。"""
    text = path.read_text(encoding="utf-8")
    return [
        stripped
        for line in text.splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    ]


def process_url(page_url: str) -> str | None:
    """访问单个详情页并解析 M3U8 URL；结果打印到 stdout，未解析到返回 None。"""
    logger.info(f"🔄 抓取页面: {page_url[:80]}...")
    m3u8_url = fetch_m3u8_from_page(page_url)
    if m3u8_url:
        logger.info("✅ 解析到 M3U8 地址")
        print(m3u8_url)
    else:
        logger.warning("⚠️  未解析到 M3U8 URL")
    return m3u8_url


def _print_stats(total: int, success: int, not_found: int) -> None:
    """打印本轮统计信息。"""
    sep = "=" * 60
    logger.info(f"\n{sep}")
    logger.info("📊 M3U8 提取统计")
    logger.info(sep)
    logger.info(f"总处理数: {total}")
    logger.info(f"成功解析: {success}")
    logger.info(f"未解析到: {not_found}")
    logger.info(f"{sep}\n")


def main(argv: list[str] | None = None) -> None:
    """主入口：解析参数 → 逐个抓取解析 → 输出结果与统计。"""
    args = parse_args(argv)

    if bool(args.page_url) == bool(args.file):
        logger.error("错误: page_url 与 --file 必须二选一")
        sys.exit(1)

    if args.page_url:
        page_urls = [args.page_url]
    else:
        if not args.file.is_file():
            logger.error(f"错误: 文件不存在: {args.file}")
            sys.exit(1)
        page_urls = read_urls_from_file(args.file)
        if not page_urls:
            logger.error(f"错误: 文件中没有有效的页面 URL: {args.file}")
            sys.exit(1)

    found_urls: list[str] = []
    not_found = 0
    for page_url in page_urls:
        try:
            m3u8_url = process_url(page_url)
        except ImportError as e:
            logger.error(f"\n❌ 依赖未安装: {e}")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"❌ [{page_url[:80]}] 处理失败: {e}")
            m3u8_url = None
        if m3u8_url:
            found_urls.append(m3u8_url)
        else:
            not_found += 1

    _print_stats(len(page_urls), len(found_urls), not_found)

    if args.output:
        args.output.write_text("".join(f"{url}\n" for url in found_urls), encoding="utf-8")
        logger.info(f"📄 结果已写入: {args.output}")

    if not found_urls:
        logger.error("❌ 未解析到任何 M3U8 URL")
        sys.exit(1)


if __name__ == "__main__":
    main()
