#!/usr/bin/env python3
"""
M3U8下载文件校验脚本
用于校验下载的文件是否完整，包括文件数量和文件大小
"""

import os
import sys
import json
from typing import Dict, List, Tuple


def parse_m3u8_file(playlist_path: str) -> List[Dict[str, any]]:
    """解析m3u8文件，提取所有片段信息"""
    segments = []

    if not os.path.exists(playlist_path):
        print(f"错误: 找不到playlist.txt文件: {playlist_path}")
        return segments

    with open(playlist_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    segment_index = 0

    for line in lines:
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith("#"):
            continue

        # 如果是URL
        if line.startswith("http") or (not line.startswith("#") and "." in line):
            # 提取文件名
            filename = os.path.basename(line)
            if not filename or not filename.endswith(".ts"):
                filename = f"segment_{segment_index:05d}.ts"

            segments.append(
                {"index": segment_index, "url": line, "expected_filename": filename}
            )
            segment_index += 1

    return segments


def get_file_size(filepath: str) -> int:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def load_content_lengths(directory: str) -> Dict[str, int]:
    """
    加载Content-Length信息

    Args:
        directory: 下载目录

    Returns:
        Dict[str, int]: 文件名到Content-Length的映射
    """
    content_lengths_file = os.path.join(directory, "content_lengths.json")

    if not os.path.exists(content_lengths_file):
        return {}

    try:
        with open(content_lengths_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def validate_content_length(filepath: str, expected_length: int) -> bool:
    """
    校验文件大小与Content-Length是否一致

    Args:
        filepath: 文件路径
        expected_length: 预期的Content-Length

    Returns:
        bool: 文件大小是否完整
    """
    try:
        actual_size = os.path.getsize(filepath)

        # 如果实际大小小于预期，则不完整
        if actual_size < expected_length:
            return False

        # 允许实际大小略大于预期（某些服务器可能有填充）
        # 但不应该大太多（最多1%或1KB）
        max_allowed = expected_length + max(expected_length * 0.01, 1024)
        if actual_size > max_allowed:
            return False

        return True

    except Exception:
        return False


def validate_downloads(directory: str) -> Tuple[bool, Dict]:
    """校验下载的文件"""
    directory = os.path.abspath(directory)

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        return False, {}

    playlist_path = os.path.join(directory, "playlist.txt")
    if not os.path.exists(playlist_path):
        print(f"错误: 找不到playlist.txt文件: {playlist_path}")
        return False, {}

    # 解析m3u8文件
    expected_segments = parse_m3u8_file(playlist_path)
    expected_count = len(expected_segments)

    # 加载Content-Length信息
    content_lengths = load_content_lengths(directory)

    # 获取目录中所有.ts文件
    ts_files = []
    for file in os.listdir(directory):
        if file.endswith(".ts"):
            filepath = os.path.join(directory, file)
            if os.path.isfile(filepath):
                ts_files.append(file)

    actual_count = len(ts_files)

    # 统计文件大小
    total_size = 0
    file_sizes = {}
    for file in ts_files:
        filepath = os.path.join(directory, file)
        size = get_file_size(filepath)
        file_sizes[file] = size
        total_size += size

    # 检查文件数量
    missing_files = []
    expected_filenames = {seg["expected_filename"] for seg in expected_segments}
    actual_filenames = set(ts_files)
    missing_files = list(expected_filenames - actual_filenames)

    # 检查文件大小
    zero_size_files = []
    incomplete_files = []

    for file in sorted(ts_files):
        filepath = os.path.join(directory, file)
        size = file_sizes[file]

        # 检查空文件
        if size == 0:
            zero_size_files.append(file)
        else:
            # 检查Content-Length
            if file in content_lengths:
                expected_length = content_lengths[file]
                if not validate_content_length(filepath, expected_length):
                    incomplete_files.append(file)

    # 收集所有失败的文件（用于获取URL）
    failed_files_set = (
        set(missing_files)
        | set(zero_size_files)
        | set(incomplete_files)
    )

    # 构建文件名到URL的映射
    filename_to_url = {
        seg["expected_filename"]: seg["url"] for seg in expected_segments
    }
    failed_urls = {}
    for filename in failed_files_set:
        if filename in filename_to_url:
            failed_urls[filename] = filename_to_url[filename]

    # 生成报告
    result = {
        "directory": directory,
        "expected_count": expected_count,
        "actual_count": actual_count,
        "missing_count": expected_count - actual_count,
        "total_size": total_size,
        "missing_files": missing_files,
        "zero_size_files": zero_size_files,
        "incomplete_files": incomplete_files,
        "failed_files": list(failed_files_set),
        "failed_urls": failed_urls,
        "is_complete": (actual_count == expected_count)
        and (len(zero_size_files) == 0)
        and (len(incomplete_files) == 0),
    }

    # 显示统计信息
    print("\n文件统计:")
    print(f"  预期文件数量: {expected_count}")
    print(f"  实际文件数量: {actual_count}")

    if result["is_complete"]:
        print("\n✅ 校验通过: 所有文件已完整下载")
    else:
        total_failed = len(failed_files_set)
        print(f"\n❌ 校验失败: 发现 {total_failed} 个失败文件")
        print("  失败文件类型统计:")
        print(f"    - 缺失: {len(missing_files)} 个")
        print(f"    - 空文件: {len(zero_size_files)} 个")
        print(f"    - 不完整: {len(incomplete_files)} 个")

        # 显示前十个失败的文件名
        failed_files_sorted = sorted(list(failed_files_set))
        if failed_files_sorted:
            print("\n  前十个失败的文件名:")
            for i, filename in enumerate(failed_files_sorted[:10], 1):
                print(f"    {i}. {filename}")
            if len(failed_files_sorted) > 10:
                print(f"    ... 还有 {len(failed_files_sorted) - 10} 个失败文件")
    print()

    return result["is_complete"], result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python validate_downloads.py <目录路径>")
        print("示例: python validate_downloads.py ./my_video")
        sys.exit(1)

    directory = sys.argv[1]
    is_complete, result = validate_downloads(directory)

    # 返回退出码
    sys.exit(0 if is_complete else 1)


if __name__ == "__main__":
    main()
