#!/usr/bin/env python3
"""
自动下载守护进程入口
从环境变量加载配置，启动自动下载器
"""

from __future__ import annotations

import argparse
import sys
import traceback

from m3u8_spider.config import (
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    DOWNLOAD_COOLDOWN_SECONDS,
    DOWNLOAD_CHECK_INTERVAL,
    get_mysql_config,
)
from m3u8_spider.automation.auto_downloader import create_auto_downloader
from m3u8_spider.logger import get_logger

# 初始化 logger
logger = get_logger(__name__)


def load_daemon_config() -> dict:
    """
    加载守护进程配置（MySQL + 可选的下载/间隔默认值）。
    由 config 模块统一加载 .env，此处仅组装并校验 MySQL。
    """
    mysql = get_mysql_config()
    return {
        **mysql,
        "DOWNLOAD_CHECK_INTERVAL": DOWNLOAD_CHECK_INTERVAL,
        "DEFAULT_CONCURRENT": DEFAULT_CONCURRENT,
        "DEFAULT_DELAY": DEFAULT_DELAY,
        "DOWNLOAD_COOLDOWN_SECONDS": DOWNLOAD_COOLDOWN_SECONDS,
    }


# ---------------------------------------------------------------------------
# CLI 解析
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="M3U8 自动下载守护进程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m cli.daemon
  python -m cli.daemon --concurrent 64 --delay 0.5
  python -m cli.daemon --check-interval 30

说明:
  - 守护进程会持续运行，从数据库读取待下载任务
  - 使用 Ctrl+C 优雅退出
  - 配置从 .env 文件或环境变量读取（参考 env.example）
        """,
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        help=f"并发下载数（默认: 从配置文件读取，或 {DEFAULT_CONCURRENT}）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        help=f"下载延迟（秒）（默认: 从配置文件读取，或 {DEFAULT_DELAY}）",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        help="检查间隔（秒）（默认: 从配置文件读取，或 60）",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        help=f"下载完成后的冷却时间（秒）（默认: 从配置文件读取，或 {DOWNLOAD_COOLDOWN_SECONDS}）",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main() -> None:
    """主入口"""
    # 打印欢迎信息
    logger.info("=" * 60)
    logger.info("🎬 M3U8 自动下载守护进程")
    logger.info("=" * 60)

    # 解析命令行参数
    args = parse_args()

    # 加载配置（.env 由 config 模块统一加载）
    try:
        config = load_daemon_config()
    except ValueError as e:
        logger.error(f"\n❌ 配置加载失败: {e}")
        sys.exit(1)

    # 命令行参数覆盖配置文件
    concurrent = (
        args.concurrent if args.concurrent is not None else config["DEFAULT_CONCURRENT"]
    )
    delay = args.delay if args.delay is not None else config["DEFAULT_DELAY"]
    check_interval = (
        args.check_interval
        if args.check_interval is not None
        else config["DOWNLOAD_CHECK_INTERVAL"]
    )
    cooldown_seconds = (
        args.cooldown
        if args.cooldown is not None
        else config["DOWNLOAD_COOLDOWN_SECONDS"]
    )

    # 创建并启动自动下载器
    try:
        downloader = create_auto_downloader(
            db_host=config["MYSQL_HOST"],
            db_port=config["MYSQL_PORT"],
            db_user=config["MYSQL_USER"],
            db_password=config["MYSQL_PASSWORD"],
            db_database=config["MYSQL_DATABASE"],
            check_interval=check_interval,
            concurrent=concurrent,
            delay=delay,
            cooldown_seconds=cooldown_seconds,
        )
        downloader.run()
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  收到键盘中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"\n❌ 发生错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()