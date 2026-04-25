#!/usr/bin/env python3
"""
M3U8 URL 刷新守护进程入口
从环境变量加载配置，对带页面 URL 的任务爬取并更新 m3u8_address
"""

from __future__ import annotations

import argparse
import sys
import traceback

from m3u8_spider.config import (
    M3U8_REFRESH_INTERVAL,
    M3U8_REFRESH_MIN_MINUTES,
    get_mysql_config,
)
from m3u8_spider.automation.m3u8_refresher import create_m3u8_refresher
from m3u8_spider.logger import get_logger

logger = get_logger(__name__)


def load_refresh_config() -> dict:
    """加载刷新守护进程配置（MySQL + 间隔等）"""
    mysql = get_mysql_config()
    return {
        **mysql,
        "M3U8_REFRESH_INTERVAL": M3U8_REFRESH_INTERVAL,
        "M3U8_REFRESH_MIN_MINUTES": M3U8_REFRESH_MIN_MINUTES,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="M3U8 URL 刷新守护进程：从页面 URL 抓取 M3U8 地址并更新数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m cli.m3u8_refresh_daemon
  python -m cli.m3u8_refresh_daemon --check-interval 300 --min-minutes 10

说明:
  - 表 movie_info 需有 url 字段（页面 URL）
  - 使用 Ctrl+C 优雅退出
  - 需安装可选依赖: pip install crawl4ai && playwright install
        """,
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        help=f"每轮间隔（秒）（默认: {M3U8_REFRESH_INTERVAL}）",
    )
    parser.add_argument(
        "--min-minutes",
        type=int,
        help=f"仅刷新 m3u8_update_time 超过此分钟数的记录（默认: {M3U8_REFRESH_MIN_MINUTES}）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="每轮最多处理任务数（默认: 30）",
    )
    return parser.parse_args()


def main() -> None:
    logger.info("=" * 60)
    logger.info("🔄 M3U8 URL 刷新守护进程")
    logger.info("=" * 60)

    args = parse_args()

    try:
        config = load_refresh_config()
    except ValueError as e:
        logger.error(f"\n❌ 配置加载失败: {e}")
        sys.exit(1)

    check_interval = (
        args.check_interval
        if args.check_interval is not None
        else config["M3U8_REFRESH_INTERVAL"]
    )
    min_minutes = (
        args.min_minutes
        if args.min_minutes is not None
        else config["M3U8_REFRESH_MIN_MINUTES"]
    )

    try:
        refresher = create_m3u8_refresher(
            db_host=config["MYSQL_HOST"],
            db_port=config["MYSQL_PORT"],
            db_user=config["MYSQL_USER"],
            db_password=config["MYSQL_PASSWORD"],
            db_database=config["MYSQL_DATABASE"],
            check_interval=check_interval,
            min_minutes_since_update=min_minutes,
            batch_size=args.batch_size,
        )
        refresher.run()
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  收到键盘中断")
        sys.exit(0)
    except ImportError as e:
        logger.error(f"\n❌ 依赖未安装: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"\n❌ 发生错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
