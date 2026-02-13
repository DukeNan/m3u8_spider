#!/usr/bin/env python3
"""
下载恢复流程：
1. 先补齐关键元数据文件
2. 再做完整性校验
3. 若不完整，仅重下失败 TS（最多 N 轮）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from utils.logger import get_logger
from utils.scrapy_manager import DownloadConfig, run_scrapy
from validate_downloads import validate_downloads

logger = get_logger(__name__)

CONTENT_LENGTHS_FILE = "content_lengths.json"
ENCRYPTION_INFO_FILE = "encryption_info.json"
ENCRYPTION_KEY_FILE = "encryption.key"
PLAYLIST_FILE = "playlist.txt"


@dataclass
class RecoveryResult:
    """恢复流程结果。"""

    is_complete: bool
    validation_result: dict
    retry_rounds: int
    metadata_downloaded: bool
    retry_history: list[int] = field(default_factory=list)


def recover_download(config: DownloadConfig, max_retry_rounds: int = 3) -> RecoveryResult:
    """
    执行下载恢复流程：
    - 补齐关键文件
    - 校验
    - 仅重下失败 TS（最多 max_retry_rounds 轮）
    """
    if config.retry_urls:
        raise ValueError("recover_download 不接受 retry_urls 配置")
    if config.metadata_only:
        raise ValueError("recover_download 不接受 metadata_only 配置")

    download_dir = config.download_dir
    download_dir.mkdir(parents=True, exist_ok=True)

    missing_metadata = _collect_missing_metadata(download_dir)
    metadata_downloaded = False

    if missing_metadata:
        logger.info(f"检测到缺失元数据文件: {', '.join(missing_metadata)}")
        logger.info("开始补齐元数据文件...")
        run_scrapy(
            DownloadConfig(
                m3u8_url=config.m3u8_url,
                filename=config.filename,
                concurrent=config.concurrent,
                delay=config.delay,
                metadata_only=True,
            )
        )
        metadata_downloaded = True

    _ensure_content_lengths_file(download_dir)

    is_complete, validation = validate_downloads(str(download_dir))
    if is_complete:
        return RecoveryResult(
            is_complete=True,
            validation_result=validation,
            retry_rounds=0,
            metadata_downloaded=metadata_downloaded,
            retry_history=[],
        )

    retry_history: list[int] = []
    retry_rounds_used = 0
    for round_index in range(1, max_retry_rounds + 1):
        retry_rounds_used = round_index
        failed_urls = _extract_failed_urls(validation)
        failed_count = len(failed_urls)
        retry_history.append(failed_count)

        if failed_count == 0:
            logger.error("校验失败但 failed_urls 为空，无法继续仅重下失败 TS")
            break

        logger.warning(
            f"第 {round_index}/{max_retry_rounds} 轮重试：仅重下 {failed_count} 个失败 TS 文件"
        )
        retry_urls = _build_retry_urls(failed_urls)

        run_scrapy(
            DownloadConfig(
                m3u8_url=config.m3u8_url,
                filename=config.filename,
                concurrent=config.concurrent,
                delay=config.delay,
                retry_urls=retry_urls,
            )
        )

        is_complete, validation = validate_downloads(str(download_dir))
        if is_complete:
            return RecoveryResult(
                is_complete=True,
                validation_result=validation,
                retry_rounds=round_index,
                metadata_downloaded=metadata_downloaded,
                retry_history=retry_history,
            )

    return RecoveryResult(
        is_complete=False,
        validation_result=validation,
        retry_rounds=retry_rounds_used,
        metadata_downloaded=metadata_downloaded,
        retry_history=retry_history,
    )


def _collect_missing_metadata(download_dir: Path) -> list[str]:
    """收集缺失的关键元数据文件。"""
    missing: list[str] = []

    base_required = [CONTENT_LENGTHS_FILE, ENCRYPTION_INFO_FILE, PLAYLIST_FILE]
    for filename in base_required:
        if not (download_dir / filename).exists():
            missing.append(filename)

    encryption_info = _load_encryption_info(download_dir)
    if _requires_encryption_key(encryption_info) and not (
        download_dir / ENCRYPTION_KEY_FILE
    ).exists():
        missing.append(ENCRYPTION_KEY_FILE)

    return missing


def _load_encryption_info(download_dir: Path) -> dict:
    """加载 encryption_info.json，异常时返回空字典。"""
    path = download_dir / ENCRYPTION_INFO_FILE
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _requires_encryption_key(encryption_info: dict) -> bool:
    """
    仅在 m3u8 标记为加密且存在 key_uri 时要求 encryption.key。
    非加密视频不强制要求该文件。
    """
    return bool(
        encryption_info.get("is_encrypted") and encryption_info.get("key_uri")
    )


def _ensure_content_lengths_file(download_dir: Path) -> None:
    """若 content_lengths.json 缺失，创建空文件，避免后续流程反复缺失。"""
    path = download_dir / CONTENT_LENGTHS_FILE
    if path.exists():
        return

    with open(path, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)


def _extract_failed_urls(validation_result: dict) -> dict[str, str]:
    """从校验结果中提取 failed_urls。"""
    if not isinstance(validation_result, dict):
        return {}
    failed_urls = validation_result.get("failed_urls", {})
    if not isinstance(failed_urls, dict):
        return {}
    return {str(filename): str(url) for filename, url in failed_urls.items() if url}


def _build_retry_urls(failed_urls: dict[str, str]) -> list[dict]:
    """将 failed_urls 转成 spider 的 retry_urls 参数格式。"""
    retry_urls: list[dict] = []
    for filename, url in sorted(failed_urls.items()):
        retry_urls.append({"url": url, "filename": filename})
    return retry_urls
