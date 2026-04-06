#!/usr/bin/env python3
"""
统一配置文件
合并原 constants.py 与 env.example 的配置项。
首次导入时加载项目根目录下的 .env 文件，环境变量可覆盖下方可覆盖项。

环境变量说明（.env 或系统环境变量）:
  - MySQL（自动下载守护进程必需）:
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
  - MySQL 客户端超时（可选，见下方常量默认值）:
    MYSQL_CONNECT_TIMEOUT, MYSQL_READ_TIMEOUT, MYSQL_WRITE_TIMEOUT
  - 可覆盖的默认值:
    DEFAULT_CONCURRENT, DEFAULT_DELAY, DOWNLOAD_COOLDOWN_SECONDS,
    DOWNLOAD_CHECK_INTERVAL, LOG_LEVEL
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env（项目根目录：m3u8_spider 包的父目录）
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


# ---------------------------------------------------------------------------
# 下载相关（可被环境变量覆盖）
# ---------------------------------------------------------------------------

_DEFAULT_CONCURRENT = 32
_DEFAULT_DELAY = 0.0
_DOWNLOAD_COOLDOWN = 30

DEFAULT_CONCURRENT: int = int(
    os.getenv("DEFAULT_CONCURRENT", str(_DEFAULT_CONCURRENT))
)
DEFAULT_DELAY: float = float(os.getenv("DEFAULT_DELAY", str(_DEFAULT_DELAY)))
DOWNLOAD_COOLDOWN_SECONDS: int = int(
    os.getenv("DOWNLOAD_COOLDOWN_SECONDS", str(_DOWNLOAD_COOLDOWN))
)

# 默认下载输出基目录（固定，不通过环境变量覆盖）
DEFAULT_BASE_DIR: str = "movies"


# ---------------------------------------------------------------------------
# 日志相关
# ---------------------------------------------------------------------------

_DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_LEVEL: str = os.getenv("LOG_LEVEL", _DEFAULT_LOG_LEVEL).upper()

LOGS_DIR: str = "logs"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# 文件相关
# ---------------------------------------------------------------------------

INVALID_FILENAME_CHARS: str = '<>:"/\\|?*'
DEFAULT_MP4_DIR: str = "mp4"


# ---------------------------------------------------------------------------
# 合并相关
# ---------------------------------------------------------------------------

TEMP_PLAYLIST_NAME: str = "temp_playlist.m3u8"
FILE_LIST_NAME: str = "file_list.txt"
ENCRYPTION_INFO_NAME: str = "encryption_info.json"
DEFAULT_KEY_FILE: str = "encryption.key"


# ---------------------------------------------------------------------------
# 自动下载守护进程专用（可被环境变量覆盖）
# ---------------------------------------------------------------------------

_DEFAULT_CHECK_INTERVAL = 60
DOWNLOAD_CHECK_INTERVAL: int = int(
    os.getenv("DOWNLOAD_CHECK_INTERVAL", str(_DEFAULT_CHECK_INTERVAL))
)


# ---------------------------------------------------------------------------
# M3U8 URL 刷新守护进程（可被环境变量覆盖）
# ---------------------------------------------------------------------------

_DEFAULT_M3U8_REFRESH_INTERVAL = 300
_DEFAULT_M3U8_REFRESH_MIN_MINUTES = 10

M3U8_REFRESH_INTERVAL: int = int(
    os.getenv("M3U8_REFRESH_INTERVAL", str(_DEFAULT_M3U8_REFRESH_INTERVAL))
)
M3U8_REFRESH_MIN_MINUTES: int = int(
    os.getenv("M3U8_REFRESH_MIN_MINUTES", str(_DEFAULT_M3U8_REFRESH_MIN_MINUTES))
)


# ---------------------------------------------------------------------------
# MySQL 客户端超时（秒，可被环境变量覆盖；避免 UPDATE 等操作无限阻塞）
# ---------------------------------------------------------------------------

_DEFAULT_MYSQL_CONNECT_TIMEOUT = 10
_DEFAULT_MYSQL_READ_TIMEOUT = 120
_DEFAULT_MYSQL_WRITE_TIMEOUT = 120

MYSQL_CONNECT_TIMEOUT: int = int(
    os.getenv("MYSQL_CONNECT_TIMEOUT", str(_DEFAULT_MYSQL_CONNECT_TIMEOUT))
)
MYSQL_READ_TIMEOUT: int = int(
    os.getenv("MYSQL_READ_TIMEOUT", str(_DEFAULT_MYSQL_READ_TIMEOUT))
)
MYSQL_WRITE_TIMEOUT: int = int(
    os.getenv("MYSQL_WRITE_TIMEOUT", str(_DEFAULT_MYSQL_WRITE_TIMEOUT))
)


# ---------------------------------------------------------------------------
# MySQL 配置（仅从环境变量读取）
# ---------------------------------------------------------------------------

_REQUIRED_MYSQL_KEYS = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
)


def get_mysql_config() -> dict[str, str | int]:
    """
    从环境变量读取 MySQL 配置并校验必需项。

    Returns:
        包含 MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE 的字典。
        MYSQL_PORT 已转为 int。

    Raises:
        ValueError: 缺少任一必需的环境变量时。
    """
    missing = [k for k in _REQUIRED_MYSQL_KEYS if not os.getenv(k)]
    if missing:
        raise ValueError(
            "缺少必需的环境变量: "
            + ", ".join(missing)
            + "。请创建 .env 或设置环境变量，参考 env.example。"
        )
    return {
        "MYSQL_HOST": os.getenv("MYSQL_HOST", ""),
        "MYSQL_PORT": int(os.getenv("MYSQL_PORT", "3306")),
        "MYSQL_USER": os.getenv("MYSQL_USER", ""),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", ""),
    }