#!/usr/bin/env python3
"""
批量合并脚本
遍历 movies/ 下的一级子目录，校验完整性、合并为 MP4、合并成功后删除源目录。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from config import DEFAULT_BASE_DIR
from merge_to_mp4 import merge_ts_files
from utils.logger import get_logger
from validate_downloads import DownloadValidator, validate_downloads

# 初始化 logger
logger = get_logger(__name__)


def _get_subdirs(movies_dir: Path) -> list[Path]:
    """获取 movies 下的一级子目录（仅目录，排除文件）"""
    if not movies_dir.is_dir():
        return []
    return sorted(p for p in movies_dir.iterdir() if p.is_dir())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="批量处理 movies/ 下的目录：校验 -> 合并 MP4 -> 删除源目录"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要处理的目录，不执行校验/合并/删除",
    )
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="执行校验和合并，但不删除源目录",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    movies_dir = project_root / DEFAULT_BASE_DIR

    subdirs = _get_subdirs(movies_dir)
    if not subdirs:
        logger.info(f"movies/ 下没有子目录，退出")
        sys.exit(0)

    if args.dry_run:
        logger.info(f"[dry-run] 将要处理 {len(subdirs)} 个目录:")
        for d in subdirs:
            playlist = d / "playlist.txt"
            has_playlist = "✓" if playlist.exists() else "✗"
            if playlist.exists():
                result = DownloadValidator(str(d)).validate()
                if result:
                    status = "✓" if result.is_complete else "✗"
                    info = f"{result.actual_count}/{result.expected_count}"
                    if not result.is_complete:
                        info += f" 缺{len(result.failed_files)}个"
                    logger.info(f"  - {d.name}  playlist:{has_playlist}  校验:{status} ({info})")
                else:
                    logger.info(f"  - {d.name}  playlist:{has_playlist}  校验:✗ (解析失败)")
            else:
                logger.info(f"  - {d.name}  playlist:{has_playlist}  校验:-")
        sys.exit(0)

    success_count = 0
    skip_count = 0
    failed_count = 0

    for subdir in subdirs:
        dir_path = str(subdir)
        dir_name = subdir.name

        playlist_path = subdir / "playlist.txt"
        if not playlist_path.exists():
            logger.warning(f"跳过 {dir_name}: 缺少 playlist.txt")
            skip_count += 1
            continue

        # 1. 校验
        logger.info(f"\n{'='*60}")
        logger.info(f"处理: {dir_name}")
        logger.info(f"{'='*60}")
        is_complete, result = validate_downloads(dir_path)

        if not is_complete:
            logger.error(f"校验失败: {dir_name}")
            failed_count += 1
            continue

        # 2. 合并
        if not merge_ts_files(dir_path, output_file=None, force_overwrite=True):
            logger.error(f"合并失败: {dir_name}")
            failed_count += 1
            continue

        # 3. 删除源目录（除非 --no-delete）
        if not args.no_delete:
            try:
                shutil.rmtree(subdir)
                logger.info(f"已删除源目录: {dir_path}")
            except OSError as e:
                logger.error(f"删除目录失败 {dir_path}: {e}")
                failed_count += 1
                continue

        success_count += 1

    # 统计
    sep = "=" * 60
    logger.info(f"\n{sep}")
    logger.info("批量处理完成")
    logger.info(sep)
    logger.info(f"成功: {success_count}")
    logger.info(f"跳过: {skip_count}")
    logger.info(f"失败: {failed_count}")
    logger.info(f"{sep}\n")


if __name__ == "__main__":
    main()
