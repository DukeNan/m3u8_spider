#!/usr/bin/env python3
"""
项目常量配置
集中管理所有常量，便于维护和修改
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 下载相关常量
# ---------------------------------------------------------------------------

# 默认并发下载数
DEFAULT_CONCURRENT: int = 32

# 默认下载延迟（秒）
DEFAULT_DELAY: float = 0.0

# 默认下载输出基目录
DEFAULT_BASE_DIR: str = "movies"

# 下载完成后的等待时间（秒）
DOWNLOAD_COOLDOWN_SECONDS: int = 30

# ---------------------------------------------------------------------------
# 日志相关常量
# ---------------------------------------------------------------------------

# 默认日志级别
DEFAULT_LOG_LEVEL: str = "INFO"

# 日志目录
LOGS_DIR: str = "logs"

# 日志格式
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 日志日期格式
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# 文件相关常量
# ---------------------------------------------------------------------------

# 文件名中不允许的字符
INVALID_FILENAME_CHARS: str = '<>:"/\\|?*'

# 默认 MP4 输出目录
DEFAULT_MP4_DIR: str = "mp4"

# ---------------------------------------------------------------------------
# 合并相关常量
# ---------------------------------------------------------------------------

# 临时播放列表文件名
TEMP_PLAYLIST_NAME: str = "temp_playlist.m3u8"

# 文件列表文件名
FILE_LIST_NAME: str = "file_list.txt"

# 加密信息文件名
ENCRYPTION_INFO_NAME: str = "encryption_info.json"

# 默认密钥文件名
DEFAULT_KEY_FILE: str = "encryption.key"
