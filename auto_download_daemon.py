#!/usr/bin/env python3
"""
自动下载守护进程入口
从环境变量加载配置，启动自动下载器
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from auto_downloader import create_auto_downloader, DOWNLOAD_COOLDOWN_SECONDS
from logger_config import get_logger
from main import DEFAULT_CONCURRENT, DEFAULT_DELAY

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------


def load_config_from_env() -> dict[str, any]:
    """
    从环境变量加载配置

    Returns:
        配置字典

    Raises:
        ValueError: 缺少必需的环境变量
    """
    # 加载 .env 文件
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"✅ 已加载配置文件: {env_path}")
    else:
        logger.warning(f"⚠️  未找到 .env 文件: {env_path}")
        logger.warning("   将尝试从系统环境变量读取配置")

    # 必需的配置项
    required_keys = [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ]

    config = {}
    missing_keys = []

    for key in required_keys:
        value = os.getenv(key)
        if not value:
            missing_keys.append(key)
        else:
            config[key] = value

    if missing_keys:
        logger.error("\n❌ 缺少必需的环境变量:")
        for key in missing_keys:
            logger.error(f"   - {key}")
        logger.error("\n请创建 .env 文件或设置环境变量")
        logger.error("参考 env.example 文件")
        raise ValueError("缺少必需的环境变量")

    # 可选的配置项
    config["DOWNLOAD_CHECK_INTERVAL"] = int(os.getenv("DOWNLOAD_CHECK_INTERVAL", "60"))
    config["DEFAULT_CONCURRENT"] = int(
        os.getenv("DEFAULT_CONCURRENT", str(DEFAULT_CONCURRENT))
    )
    config["DEFAULT_DELAY"] = float(os.getenv("DEFAULT_DELAY", str(DEFAULT_DELAY)))
    config["DOWNLOAD_COOLDOWN_SECONDS"] = int(
        os.getenv("DOWNLOAD_COOLDOWN_SECONDS", str(DOWNLOAD_COOLDOWN_SECONDS))
    )

    return config


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
  python auto_download_daemon.py
  python auto_download_daemon.py --concurrent 64 --delay 0.5
  python auto_download_daemon.py --check-interval 30

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

    # 加载配置
    try:
        config = load_config_from_env()
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
            db_port=int(config["MYSQL_PORT"]),
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
        logger.error(f"\n❌ 发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
