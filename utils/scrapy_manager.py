#!/usr/bin/env python3
"""
Scrapy 管理模块
负责 Scrapy 爬虫的配置和运行
"""

from __future__ import annotations

import subprocess
import sys
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from pathlib import Path

from constants import (
    DEFAULT_BASE_DIR,
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    INVALID_FILENAME_CHARS,
    LOGS_DIR,
)

from utils.logger import get_logger

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DownloadConfig:
    """
    M3U8 下载配置（不可变）

    Attributes:
        m3u8_url: M3U8 播放列表的 URL
        filename: 保存的文件名
        concurrent: 并发下载数
        delay: 下载延迟（秒）
        metadata_only: 仅下载/补齐元数据文件（playlist、加密信息、密钥、content_lengths）
        retry_urls: 重试模式参数（可选）。
                   如果提供此参数，spider 将跳过 M3U8 解析，直接下载指定的视频片段。
                   每个字典应包含：
                   - url: 视频片段的 URL
                   - filename: 保存的文件名
                   - index (可选): 片段索引，默认为 0

                   示例：
                   [
                       {"url": "https://example.com/segment1.ts", "filename": "segment_00001.ts", "index": 0},
                       {"url": "https://example.com/segment2.ts", "filename": "segment_00002.ts", "index": 1}
                   ]
    """

    m3u8_url: str
    filename: str
    concurrent: int = DEFAULT_CONCURRENT
    delay: float = DEFAULT_DELAY
    metadata_only: bool = False
    retry_urls: list[dict] | None = None  # 重试模式：直接下载指定的视频片段列表

    def __post_init__(self) -> None:
        if not self.m3u8_url.startswith(("http://", "https://")):
            raise ValueError(f"无效的URL: {self.m3u8_url}")
        if not self.filename or not self.filename.strip():
            raise ValueError("文件名不能为空")
        if self.metadata_only and self.retry_urls:
            raise ValueError("metadata_only 与 retry_urls 不能同时启用")

    @property
    def sanitized_filename(self) -> str:
        """清理后的文件名（移除不合法字符）"""
        name = self.filename.strip()
        for char in INVALID_FILENAME_CHARS:
            name = name.replace(char, "_")
        return name

    @property
    def project_root(self) -> Path:
        """项目根目录（utils 的父目录）"""
        return Path(__file__).resolve().parent.parent

    @property
    def scrapy_project_dir(self) -> Path:
        """Scrapy 项目目录"""
        return self.project_root / "scrapy_project"

    @property
    def download_dir(self) -> Path:
        """下载输出目录路径（默认在 movies/ 下）"""
        return self.project_root / DEFAULT_BASE_DIR / self.sanitized_filename


# ---------------------------------------------------------------------------
# Scrapy 运行函数
# ---------------------------------------------------------------------------


def run_scrapy(config: DownloadConfig) -> None:
    """
    使用 subprocess 调用 scrapy crawl 命令运行爬虫。

    Args:
        config: 下载配置

    注意：
    - 使用 subprocess 调用 scrapy crawl 命令，支持标准的 Scrapy 命令行参数传递方式
    - 通过 -a 参数传递 spider 参数
    - 通过 -s 参数设置 Scrapy settings
    """
    # 确保目录存在
    config.download_dir.parent.mkdir(parents=True, exist_ok=True)
    log_dir = config.project_root / LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{config.sanitized_filename}.log"

    # 构建 scrapy crawl 命令
    # m3u8_url 通过 base64 传递，避免 URL 中的特殊字符影响 -a name=value 解析
    m3u8_url_b64 = urlsafe_b64encode(config.m3u8_url.encode("utf-8")).decode("ascii")
    cmd = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "m3u8_downloader",
        "-a",
        f"m3u8_url_b64={m3u8_url_b64}",
        "-a",
        f"filename={config.sanitized_filename}",
        "-a",
        f"download_directory={config.download_dir}",
        "-s",
        f"CONCURRENT_REQUESTS={config.concurrent}",
        "-s",
        f"DOWNLOAD_DELAY={config.delay}",
        "-s",
        f"M3U8_LOG_FILE={log_file}",
    ]

    # 如果存在 retry_urls，需要序列化为 JSON 字符串传递
    if config.retry_urls:
        import json

        retry_urls_json = json.dumps(config.retry_urls)
        cmd.extend(["-a", f"retry_urls={retry_urls_json}"])

    if config.metadata_only:
        cmd.extend(["-a", "metadata_only=1"])

    logger.info(f"执行命令: {' '.join(cmd)}")
    logger.info(f"日志文件: {log_file}")

    # 在 scrapy_project 目录下运行命令
    # 不捕获输出，让日志实时显示在控制台
    # 同时通过 M3U8FileLogExtension 将日志写入文件（控制台+文件双输出）
    subprocess.run(
        cmd,
        cwd=str(config.scrapy_project_dir),
        check=True,
        # 不捕获输出，确保日志实时显示在控制台
        # Scrapy 的 M3U8FileLogExtension 会同时将日志写入文件
        capture_output=False,
    )
