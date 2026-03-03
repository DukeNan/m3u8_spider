"""
M3U8 Spider - M3U8视频下载工具包

提供:
- config: 配置管理
- logger: 日志工具
- core.downloader: Scrapy下载管理
- core.recovery: 下载恢复流程
- core.validator: 下载校验
- database.manager: 数据库管理
- automation.auto_downloader: 自动下载守护进程
- utils.merger: TS合并工具
- utils.migration: 数据库迁移工具
"""

from __future__ import annotations

__version__ = "0.1.0"

# 便捷导入
from m3u8_spider.config import (
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    DEFAULT_BASE_DIR,
    LOGS_DIR,
    get_mysql_config,
)
from m3u8_spider.logger import get_logger

__all__ = [
    "DEFAULT_CONCURRENT",
    "DEFAULT_DELAY",
    "DEFAULT_BASE_DIR",
    "LOGS_DIR",
    "get_mysql_config",
    "get_logger",
]