#!/usr/bin/env python3
"""
M3U8下载文件校验脚本
用于校验下载的文件是否完整，包括文件数量和文件大小
"""

import os
import sys
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Tuple


def parse_m3u8_file(playlist_path: str) -> List[Dict[str, any]]:
    """解析m3u8文件，提取所有片段信息"""
    segments = []

    if not os.path.exists(playlist_path):
        print(f"错误: 找不到playlist.txt文件: {playlist_path}")
        return segments

    with open(playlist_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.strip().split('\n')
    segment_index = 0

    for line in lines:
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith('#'):
            continue

        # 如果是URL
        if line.startswith('http') or (not line.startswith('#') and '.' in line):
            # 提取文件名
            filename = os.path.basename(line)
            if not filename or not filename.endswith('.ts'):
                filename = f"segment_{segment_index:05d}.ts"

            segments.append({
                'index': segment_index,
                'url': line,
                'expected_filename': filename
            })
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
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


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

    print(f"\n{'='*60}")
    print(f"校验目录: {directory}")
    print(f"{'='*60}")
    print(f"预期文件数量: {expected_count}")

    # 获取目录中所有.ts文件
    ts_files = []
    for file in os.listdir(directory):
        if file.endswith('.ts'):
            filepath = os.path.join(directory, file)
            if os.path.isfile(filepath):
                ts_files.append(file)

    actual_count = len(ts_files)
    print(f"实际文件数量: {actual_count}")

    # 统计文件大小
    total_size = 0
    file_sizes = {}
    for file in ts_files:
        filepath = os.path.join(directory, file)
        size = get_file_size(filepath)
        file_sizes[file] = size
        total_size += size

    print(f"总文件大小: {format_size(total_size)}")
    print(f"{'='*60}\n")

    # 检查文件数量
    missing_files = []
    if actual_count < expected_count:
        print(f"⚠️  警告: 文件数量不匹配！缺少 {expected_count - actual_count} 个文件")

        # 找出缺失的文件
        expected_filenames = {seg['expected_filename'] for seg in expected_segments}
        actual_filenames = set(ts_files)
        missing_files = list(expected_filenames - actual_filenames)

        if missing_files:
            print(f"\n缺失的文件:")
            for filename in sorted(missing_files):
                print(f"  - {filename}")
    elif actual_count > expected_count:
        print(f"⚠️  警告: 实际文件数量 ({actual_count}) 多于预期 ({expected_count})")
    else:
        print(f"✅ 文件数量匹配")

    # 检查文件大小
    print(f"\n文件大小统计:")
    zero_size_files = []
    for file in sorted(ts_files):
        size = file_sizes[file]
        if size == 0:
            zero_size_files.append(file)
            print(f"  ⚠️  {file}: {format_size(size)} (空文件!)")
        else:
            print(f"  ✓  {file}: {format_size(size)}")

    if zero_size_files:
        print(f"\n⚠️  警告: 发现 {len(zero_size_files)} 个空文件!")

    # 生成报告
    result = {
        'directory': directory,
        'expected_count': expected_count,
        'actual_count': actual_count,
        'missing_count': expected_count - actual_count,
        'total_size': total_size,
        'missing_files': missing_files,
        'zero_size_files': zero_size_files,
        'is_complete': (actual_count == expected_count) and (len(zero_size_files) == 0)
    }

    print(f"\n{'='*60}")
    if result['is_complete']:
        print(f"✅ 校验通过: 所有文件已完整下载")
    else:
        print(f"❌ 校验失败: 文件不完整")
    print(f"{'='*60}\n")

    return result['is_complete'], result


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
