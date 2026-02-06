#!/usr/bin/env python3
"""
M3U8 TS文件合并脚本
使用ffmpeg将下载的ts文件合并为mp4格式
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量与数据模型
# ---------------------------------------------------------------------------

TEMP_PLAYLIST_NAME = "temp_playlist.m3u8"
FILE_LIST_NAME = "file_list.txt"
ENCRYPTION_INFO_NAME = "encryption_info.json"
DEFAULT_KEY_FILE = "encryption.key"
DEFAULT_BASE_DIR = "movies"
DEFAULT_MP4_DIR = "mp4"


def _resolve_directory(arg: str) -> str:
    """
    解析目录参数：绝对路径或含路径分隔符时原样使用，否则视为视频名，解析为 movies/<name>。
    """
    if Path(arg).is_absolute():
        return arg
    if "/" in arg or "\\" in arg:
        return arg
    project_root = Path(__file__).resolve().parent
    return str(project_root / DEFAULT_BASE_DIR / arg)


@dataclass
class EncryptionInfo:
    """加密信息（从 encryption_info.json 加载）"""

    is_encrypted: bool
    method: str = "AES-128"
    key_file: str = DEFAULT_KEY_FILE
    iv: str | None = None

    @classmethod
    def from_directory(cls, directory: str) -> EncryptionInfo | None:
        """
        从下载目录加载加密信息

        Args:
            directory: 下载目录

        Returns:
            加密信息；若文件不存在或解析失败则返回 None
        """
        path = Path(directory) / ENCRYPTION_INFO_NAME
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
        return cls(
            is_encrypted=data.get("is_encrypted", False),
            method=data.get("method", "AES-128"),
            key_file=data.get("key_file", DEFAULT_KEY_FILE),
            iv=data.get("iv"),
        )


# ---------------------------------------------------------------------------
# FFmpeg 与 TS 列表
# ---------------------------------------------------------------------------


class FFmpegChecker:
    """检查 ffmpeg 是否可用（单一职责）"""

    @staticmethod
    def is_available() -> bool:
        """检查 ffmpeg 是否安装"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def print_install_help() -> None:
        """打印安装 ffmpeg 的提示"""
        print("错误: 未找到ffmpeg，请先安装ffmpeg")
        print("安装方法:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  Windows: 从 https://ffmpeg.org/download.html 下载")


def _ts_sort_key(filepath: str) -> int | str:
    """排序键：优先按文件名中的数字，否则按文件名"""
    filename = Path(filepath).name
    numbers = re.findall(r"\d+", filename)
    if numbers:
        return int(numbers[0])
    return filename


class TSFileCollector:
    """获取目录中所有 .ts 文件并按约定排序"""

    @staticmethod
    def collect(directory: str) -> list[str]:
        """获取目录中所有 ts 文件（绝对路径），按文件名数字排序"""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            print(f"错误: 目录不存在: {directory}")
            return []

        paths = []
        for p in dir_path.iterdir():
            if p.suffix == ".ts" and p.is_file():
                paths.append(str(p))
        paths.sort(key=_ts_sort_key)
        return paths


# ---------------------------------------------------------------------------
# 临时文件构建（保留原有逻辑与注释）
# ---------------------------------------------------------------------------


def _create_temp_m3u8(
    directory: str,
    ts_files: list[str],
    encryption_info: EncryptionInfo | None,
) -> str:
    """
    创建临时的 m3u8 文件

    Args:
        directory: 下载目录
        ts_files: TS 文件列表（绝对路径）
        encryption_info: 加密信息（可为 None）

    Returns:
        临时 m3u8 文件路径
    """
    path = Path(directory) / TEMP_PLAYLIST_NAME
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n")
        f.write("#EXT-X-TARGETDURATION:10\n")

        if encryption_info and encryption_info.is_encrypted:
            key_path = Path(directory) / encryption_info.key_file
            key_uri = f"file://{key_path.resolve()}"
            key_line = f'#EXT-X-KEY:METHOD={encryption_info.method},URI="{key_uri}"'
            if encryption_info.iv:
                key_line += f',IV={encryption_info.iv}'
            f.write(key_line + "\n")

        for ts_file in ts_files:
            f.write("#EXTINF:10.0,\n")
            f.write(f"{Path(ts_file).resolve()}\n")
        f.write("#EXT-X-ENDLIST\n")
    return str(path)


def _create_file_list(ts_files: list[str], list_filename: str) -> str:
    """创建 ffmpeg concat 文件列表"""
    list_path = Path(ts_files[0]).parent / list_filename
    with open(list_path, "w", encoding="utf-8") as f:
        for ts_file in ts_files:
            abs_path = str(Path(ts_file).resolve())
            abs_path = abs_path.replace("'", "'\\''")
            f.write(f"file '{abs_path}'\n")
    return str(list_path)


# ---------------------------------------------------------------------------
# 合并执行器
# ---------------------------------------------------------------------------


class MP4Merger:
    """
    将目录中的 TS 文件合并为 MP4。
    负责：检查环境、解析加密信息、收集 TS、解析输出路径、确认覆盖、调用 ffmpeg、清理临时文件。
    """

    def __init__(self, directory: str, output_file: str | None = None) -> None:
        self._directory = str(Path(directory).resolve())
        self._output_file = output_file

    def run(self) -> bool:
        """执行合并，成功返回 True，失败返回 False（含打印错误与清理）"""
        if not self._ensure_directory():
            return False
        if not self._ensure_ffmpeg():
            return False

        encryption = EncryptionInfo.from_directory(self._directory)
        is_encrypted = encryption is not None and encryption.is_encrypted

        if is_encrypted and encryption:
            if not self._check_encryption_key(encryption):
                return False
            self._print_encryption_detected(encryption)
        else:
            print("✅ 未检测到加密，将使用普通方式合并")

        ts_files = TSFileCollector.collect(self._directory)
        if not ts_files:
            print(f"错误: 在目录 {self._directory} 中未找到.ts文件")
            return False

        self._print_merge_header(ts_files)

        output_path = self._resolve_output_path()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if not self._confirm_overwrite(output_path):
            return False
        print(f"输出文件: {output_path}\n")

        temp_files: list[str] = []
        try:
            if is_encrypted and encryption:
                temp_files = self._run_encrypted(ts_files, output_path, encryption)
            else:
                temp_files = self._run_concat(ts_files, output_path)
            self._cleanup(temp_files)
            return self._print_success(output_path)
        except subprocess.CalledProcessError as e:
            print(f"错误: ffmpeg执行失败: {e}")
            self._cleanup(temp_files)
            return False
        except Exception as e:
            print(f"错误: {e}")
            self._cleanup(temp_files)
            return False

    def _ensure_directory(self) -> bool:
        if not Path(self._directory).is_dir():
            print(f"错误: 目录不存在: {self._directory}")
            return False
        return True

    def _ensure_ffmpeg(self) -> bool:
        if not FFmpegChecker.is_available():
            FFmpegChecker.print_install_help()
            return False
        return True

    def _check_encryption_key(self, encryption: EncryptionInfo) -> bool:
        key_path = Path(self._directory) / encryption.key_file
        if not key_path.exists():
            print(f"错误: 密钥文件不存在: {key_path}")
            print("提示: 请确保在下载时已正确下载密钥文件")
            return False
        return True

    def _print_encryption_detected(self, encryption: EncryptionInfo) -> None:
        print("⚠️  检测到加密的m3u8文件")
        print(f"   加密方法: {encryption.method}")
        print(f"   密钥文件: {encryption.key_file}")

    def _print_merge_header(self, ts_files: list[str]) -> None:
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"合并目录: {self._directory}")
        print(f"找到 {len(ts_files)} 个TS文件")
        print(f"{sep}\n")

    def _resolve_output_path(self) -> str:
        project_root = Path(__file__).resolve().parent
        mp4_dir = project_root / DEFAULT_MP4_DIR
        if not self._output_file:
            dir_name = Path(self._directory.rstrip("/")).name
            return str(mp4_dir / f"{dir_name}.mp4")
        if Path(self._output_file).is_absolute():
            return self._output_file
        return str(mp4_dir / Path(self._output_file).name)

    def _confirm_overwrite(self, output_path: str) -> bool:
        if not Path(output_path).exists():
            return True
        response = input(f"输出文件已存在: {output_path}\n是否覆盖? (y/n): ")
        if response.lower() != "y":
            print("已取消操作")
            return False
        return True

    def _run_encrypted(
        self,
        ts_files: list[str],
        output_path: str,
        encryption: EncryptionInfo,
    ) -> list[str]:
        """加密文件：使用 FFmpeg HLS demuxer；返回需清理的临时文件列表"""
        print("使用FFmpeg HLS demuxer处理加密文件...")
        temp_m3u8 = _create_temp_m3u8(self._directory, ts_files, encryption)
        print(f"创建临时M3U8文件: {temp_m3u8}")

        cmd = [
            "ffmpeg",
            "-allowed_extensions", "ALL",
            "-i", temp_m3u8,
            "-c", "copy",
            "-y", output_path,
        ]
        print("\n开始合并加密文件...")
        print(f"命令: {' '.join(cmd)}\n")
        subprocess.run(cmd, check=True, capture_output=False, text=True)
        return [temp_m3u8]

    def _run_concat(
        self,
        ts_files: list[str],
        output_path: str,
    ) -> list[str]:
        """未加密：使用 concat demuxer；返回需清理的临时文件列表"""
        print("使用concat demuxer合并文件...")
        list_file = _create_file_list(ts_files, FILE_LIST_NAME)
        print(f"创建文件列表: {list_file}")

        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "-y", output_path,
        ]
        print("\n开始合并...")
        print(f"命令: {' '.join(cmd)}\n")
        subprocess.run(cmd, check=True, capture_output=False, text=True)
        return [list_file]

    @staticmethod
    def _cleanup(paths: list[str]) -> None:
        for path in paths:
            p = Path(path)
            if p.exists():
                p.unlink()

    def _print_success(self, output_path: str) -> bool:
        path = Path(output_path)
        if not path.exists():
            print("错误: 合并完成但输出文件不存在")
            return False
        file_size = path.stat().st_size
        size_mb = file_size / (1024 * 1024)
        sep = "=" * 60
        print(f"\n{sep}")
        print("✅ 合并成功!")
        print(f"输出文件: {output_path}")
        print(f"文件大小: {size_mb:.2f} MB")
        print(f"{sep}\n")
        return True


# ---------------------------------------------------------------------------
# 兼容原有接口与入口
# ---------------------------------------------------------------------------


def merge_ts_files(directory: str, output_file: str | None = None) -> bool:
    """合并 ts 文件为 mp4（保留原有函数接口）"""
    return MP4Merger(directory, output_file).run()


def main() -> None:
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python merge_to_mp4.py <目录路径或视频名> [输出文件名]")
        print("示例: python merge_to_mp4.py my_video           # 默认合并 movies/my_video，输出到 mp4/my_video.mp4")
        print("      python merge_to_mp4.py my_video output.mp4  # 输出到 mp4/output.mp4")
        print("      python merge_to_mp4.py ./my_video output.mp4")
        sys.exit(1)

    directory = _resolve_directory(sys.argv[1])
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    success = merge_ts_files(directory, output_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
