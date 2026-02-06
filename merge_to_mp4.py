#!/usr/bin/env python3
"""
M3U8 TS文件合并脚本
使用ffmpeg将下载的ts文件合并为mp4格式
"""

import os
import sys
import subprocess
import re
import json
from typing import List, Optional, Dict


def check_ffmpeg() -> bool:
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_ts_files(directory: str) -> List[str]:
    """获取目录中所有ts文件，按文件名排序"""
    ts_files = []

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        return ts_files

    # 获取所有.ts文件
    for file in os.listdir(directory):
        if file.endswith(".ts"):
            filepath = os.path.join(directory, file)
            if os.path.isfile(filepath):
                ts_files.append(filepath)

    # 排序：尝试按文件名中的数字排序
    def sort_key(filepath):
        filename = os.path.basename(filepath)
        # 尝试提取文件名中的数字
        numbers = re.findall(r"\d+", filename)
        if numbers:
            return int(numbers[0])
        return filename

    ts_files.sort(key=sort_key)
    return ts_files


def load_encryption_info(directory: str) -> Optional[Dict]:
    """
    加载加密信息

    Args:
        directory: 下载目录

    Returns:
        Dict: 加密信息字典，如果不存在返回None
    """
    encryption_info_path = os.path.join(directory, "encryption_info.json")

    if not os.path.exists(encryption_info_path):
        return None

    try:
        with open(encryption_info_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def create_hls_key_info_file(directory: str, key_file: str) -> str:
    """
    创建FFmpeg密钥信息文件

    Args:
        directory: 下载目录
        key_file: 密钥文件名

    Returns:
        str: 密钥信息文件路径
    """
    key_info_path = os.path.join(directory, "key_info.txt")
    key_file_path = os.path.join(directory, key_file)

    with open(key_info_path, "w", encoding="utf-8") as f:
        # 第一行：密钥文件的绝对路径
        f.write(f"{os.path.abspath(key_file_path)}\n")
        # 第二行：密钥URL（可选，留空）
        f.write("\n")

    return key_info_path


def create_temp_m3u8(
    directory: str, ts_files: List[str], encryption_info: Optional[Dict] = None
) -> str:
    """
    创建临时的m3u8文件

    Args:
        directory: 下载目录
        ts_files: TS文件列表（绝对路径）
        encryption_info: 加密信息字典

    Returns:
        str: 临时m3u8文件路径
    """
    temp_m3u8_path = os.path.join(directory, "temp_playlist.m3u8")

    with open(temp_m3u8_path, "w", encoding="utf-8") as f:
        # 写入M3U8头部
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n")
        f.write("#EXT-X-TARGETDURATION:10\n")

        # 如果加密，写入EXT-X-KEY标签
        if encryption_info and encryption_info.get("is_encrypted"):
            key_file_path = os.path.join(directory, encryption_info.get("key_file", "encryption.key"))
            key_uri = f"file://{os.path.abspath(key_file_path)}"

            key_line = f'#EXT-X-KEY:METHOD={encryption_info.get("method", "AES-128")},URI="{key_uri}"'

            # 如果有IV，添加IV参数
            if encryption_info.get("iv"):
                key_line += f',IV={encryption_info["iv"]}'

            f.write(key_line + "\n")

        # 写入所有TS文件
        for ts_file in ts_files:
            f.write("#EXTINF:10.0,\n")
            # 使用绝对路径
            f.write(f"{os.path.abspath(ts_file)}\n")

        # 写入结束标签
        f.write("#EXT-X-ENDLIST\n")

    return temp_m3u8_path


def create_file_list(ts_files: List[str], list_file: str) -> str:
    """创建ffmpeg文件列表"""
    list_path = os.path.join(os.path.dirname(ts_files[0]), list_file)

    with open(list_path, "w", encoding="utf-8") as f:
        for ts_file in ts_files:
            # 使用绝对路径，并转义特殊字符
            abs_path = os.path.abspath(ts_file)
            # 转义单引号和反斜杠
            abs_path = abs_path.replace("'", "'\\''")
            f.write(f"file '{abs_path}'\n")

    return list_path


def merge_ts_files(directory: str, output_file: Optional[str] = None) -> bool:
    """合并ts文件为mp4"""
    directory = os.path.abspath(directory)

    if not os.path.isdir(directory):
        print(f"错误: 目录不存在: {directory}")
        return False

    # 检查ffmpeg
    if not check_ffmpeg():
        print("错误: 未找到ffmpeg，请先安装ffmpeg")
        print("安装方法:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  Windows: 从 https://ffmpeg.org/download.html 下载")
        return False

    # 检测加密状态
    encryption_info = load_encryption_info(directory)
    is_encrypted = encryption_info and encryption_info.get("is_encrypted", False)

    if is_encrypted:
        print("⚠️  检测到加密的m3u8文件")
        print(f"   加密方法: {encryption_info.get('method', 'Unknown')}")

        # 检查密钥文件是否存在
        key_file = encryption_info.get("key_file", "encryption.key")
        key_file_path = os.path.join(directory, key_file)

        if not os.path.exists(key_file_path):
            print(f"错误: 密钥文件不存在: {key_file_path}")
            print("提示: 请确保在下载时已正确下载密钥文件")
            return False

        print(f"   密钥文件: {key_file}")
    else:
        print("✅ 未检测到加密，将使用普通方式合并")

    # 获取ts文件列表
    ts_files = get_ts_files(directory)

    if not ts_files:
        print(f"错误: 在目录 {directory} 中未找到.ts文件")
        return False

    print(f"\n{'=' * 60}")
    print(f"合并目录: {directory}")
    print(f"找到 {len(ts_files)} 个TS文件")
    print(f"{'=' * 60}\n")

    # 确定输出文件名
    if not output_file:
        # 使用目录名作为输出文件名
        dir_name = os.path.basename(directory.rstrip("/"))
        output_file = os.path.join(directory, f"{dir_name}.mp4")
    else:
        # 如果输出文件不是绝对路径，则相对于目录
        if not os.path.isabs(output_file):
            output_file = os.path.join(directory, output_file)

    # 如果输出文件已存在，询问是否覆盖
    if os.path.exists(output_file):
        response = input(f"输出文件已存在: {output_file}\n是否覆盖? (y/n): ")
        if response.lower() != "y":
            print("已取消操作")
            return False

    print(f"输出文件: {output_file}\n")

    temp_files = []  # 用于清理临时文件

    try:
        if is_encrypted:
            # 加密文件：使用FFmpeg的HLS demuxer和密钥信息文件
            print("使用FFmpeg HLS demuxer处理加密文件...")

            # 创建临时m3u8文件
            temp_m3u8 = create_temp_m3u8(directory, ts_files, encryption_info)
            temp_files.append(temp_m3u8)
            print(f"创建临时M3U8文件: {temp_m3u8}")

            # 构建ffmpeg命令（使用HLS demuxer）
            cmd = [
                "ffmpeg",
                "-allowed_extensions",
                "ALL",
                "-i",
                temp_m3u8,
                "-c",
                "copy",  # 直接复制流，不重新编码
                "-y",  # 覆盖输出文件
                output_file,
            ]

            print("\n开始合并加密文件...")
            print(f"命令: {' '.join(cmd)}\n")

            # 执行ffmpeg命令
            result = subprocess.run(cmd, check=True, capture_output=False, text=True)

        else:
            # 未加密文件：使用concat demuxer（原有方法）
            print("使用concat demuxer合并文件...")

            # 创建文件列表
            list_file = create_file_list(ts_files, "file_list.txt")
            temp_files.append(list_file)
            print(f"创建文件列表: {list_file}")

            # 构建ffmpeg命令
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-c",
                "copy",  # 直接复制流，不重新编码（速度快）
                "-y",  # 覆盖输出文件
                output_file,
            ]

            print("\n开始合并...")
            print(f"命令: {' '.join(cmd)}\n")

            # 执行ffmpeg命令
            result = subprocess.run(cmd, check=True, capture_output=False, text=True)

        # 清理临时文件
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        if result.returncode == 0:
            # 检查输出文件是否存在
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                size_mb = file_size / (1024 * 1024)
                print(f"\n{'=' * 60}")
                print("✅ 合并成功!")
                print(f"输出文件: {output_file}")
                print(f"文件大小: {size_mb:.2f} MB")
                print(f"{'=' * 60}\n")
                return True
            else:
                print("错误: 合并完成但输出文件不存在")
                return False
        else:
            print("错误: ffmpeg执行失败")
            return False

    except subprocess.CalledProcessError as e:
        print(f"错误: ffmpeg执行失败: {e}")
        # 清理临时文件
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return False
    except Exception as e:
        print(f"错误: {e}")
        # 清理临时文件
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python merge_to_mp4.py <目录路径> [输出文件名]")
        print("示例: python merge_to_mp4.py ./my_video")
        print("示例: python merge_to_mp4.py ./my_video output.mp4")
        sys.exit(1)

    directory = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    success = merge_ts_files(directory, output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
