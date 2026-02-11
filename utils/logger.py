#!/usr/bin/env python3
"""
统一日志配置模块
提供标准化的日志配置，支持控制台和文件双重输出
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from constants import (
    DEFAULT_LOG_LEVEL,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
)


# ---------------------------------------------------------------------------
# 日志配置函数
# ---------------------------------------------------------------------------


def setup_logger(
    name: str | None = None,
    log_level: str | None = None,
    log_file: str | Path | None = None,
    console: bool = True,
) -> logging.Logger:
    """
    设置并返回配置好的 logger

    Args:
        name: Logger 名称（通常使用 __name__），None 时使用根 logger
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL），None 时从环境变量读取或使用默认值
        log_file: 日志文件路径，None 时不输出到文件
        console: 是否输出到控制台，默认 True

    Returns:
        配置好的 Logger 实例
    """
    # 获取 logger
    logger = logging.getLogger(name) if name else logging.root

    # 如果 logger 已经有 handlers，说明已经配置过，直接返回
    if logger.handlers:
        return logger

    # 设置日志级别
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    try:
        level = getattr(logging, log_level)
    except AttributeError:
        level = getattr(logging, DEFAULT_LOG_LEVEL)
        print(
            f"警告: 无效的日志级别 '{log_level}'，使用默认级别 '{DEFAULT_LOG_LEVEL}'",
            file=sys.stderr,
        )

    logger.setLevel(level)

    # 创建格式化器
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # 添加控制台 handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 添加文件 handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(
            log_path, mode="a", encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    获取已配置的 logger（如果未配置则使用默认配置）

    Args:
        name: Logger 名称（通常使用 __name__），None 时使用根 logger

    Returns:
        Logger 实例
    """
    logger = logging.getLogger(name) if name else logging.root

    # 如果 logger 还没有 handlers，使用默认配置
    if not logger.handlers:
        setup_logger(name=name)

    return logger
