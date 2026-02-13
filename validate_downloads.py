#!/usr/bin/env python3
"""
M3U8下载文件校验脚本
用于校验下载的文件是否完整，包括文件数量和文件大小
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from config import DEFAULT_BASE_DIR
from utils.logger import get_logger

# 初始化 logger
logger = get_logger(__name__)


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


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SegmentInfo:
    """单个 M3U8 片段信息"""

    index: int
    url: str
    expected_filename: str

    def __repr__(self) -> str:
        return f"SegmentInfo(index={self.index}, filename={self.expected_filename!r})"


@dataclass
class ValidationResult:
    """校验结果：目录统计、缺失/空/不完整文件列表、是否通过"""

    directory: str
    expected_count: int
    actual_count: int
    total_size: int
    missing_files: list[str]
    zero_size_files: list[str]
    incomplete_files: list[str]
    failed_urls: dict[str, str] = field(default_factory=dict)

    @property
    def failed_files(self) -> list[str]:
        """所有失败文件（缺失 + 空 + 不完整）去重后排序"""
        s = (
            set(self.missing_files)
            | set(self.zero_size_files)
            | set(self.incomplete_files)
        )
        return sorted(s)

    @property
    def is_complete(self) -> bool:
        """是否校验通过"""
        return (
            self.actual_count == self.expected_count
            and len(self.zero_size_files) == 0
            and len(self.incomplete_files) == 0
        )

    def to_legacy_dict(self) -> dict:
        """兼容原有返回的字典格式"""
        return {
            "directory": self.directory,
            "expected_count": self.expected_count,
            "actual_count": self.actual_count,
            "missing_count": self.expected_count - self.actual_count,
            "total_size": self.total_size,
            "missing_files": self.missing_files,
            "zero_size_files": self.zero_size_files,
            "incomplete_files": self.incomplete_files,
            "failed_files": self.failed_files,
            "failed_urls": self.failed_urls,
            "is_complete": self.is_complete,
        }


# ---------------------------------------------------------------------------
# 解析与加载
# ---------------------------------------------------------------------------


class PlaylistParser:
    """解析 m3u8/playlist 文件，提取所有片段信息（单一职责）"""

    @staticmethod
    def parse(playlist_path: str) -> list[SegmentInfo]:
        """解析 m3u8 文件，提取所有片段信息"""
        segments: list[SegmentInfo] = []

        if not Path(playlist_path).exists():
            logger.error(f"错误: 找不到playlist.txt文件: {playlist_path}")
            return segments

        content = PlaylistParser._read_file(playlist_path)
        segment_index = 0

        for line in content.strip().split("\n"):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 如果是 URL
            if line.startswith("http") or (not line.startswith("#") and "." in line):
                filename = Path(line).name
                if not filename or not filename.endswith(".ts"):
                    filename = f"segment_{segment_index:05d}.ts"

                segments.append(
                    SegmentInfo(
                        index=segment_index, url=line, expected_filename=filename
                    )
                )
                segment_index += 1

        return segments

    @staticmethod
    def _read_file(path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class ContentLengthLoader:
    """
    加载 Content-Length 信息（文件名 → 预期字节数）
    """

    _FILENAME = "content_lengths.json"

    @classmethod
    def load(cls, directory: str) -> dict[str, int]:
        """
        加载 Content-Length 信息

        Args:
            directory: 下载目录

        Returns:
            文件名到 Content-Length 的映射
        """
        path = Path(directory) / cls._FILENAME
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# 校验逻辑
# ---------------------------------------------------------------------------


def _get_file_size(filepath: str) -> int:
    """获取文件大小（字节）"""
    try:
        return Path(filepath).stat().st_size
    except OSError:
        return 0


def _validate_content_length(filepath: str, expected_length: int) -> bool:
    """
    校验文件大小与 Content-Length 是否一致

    Args:
        filepath: 文件路径
        expected_length: 预期的 Content-Length

    Returns:
        文件大小是否完整
    """
    try:
        actual_size = Path(filepath).stat().st_size

        # 如果实际大小小于预期，则不完整
        if actual_size < expected_length:
            return False

        # 允许实际大小略大于预期（某些服务器可能有填充）
        # 但不应该大太多（最多 1% 或 1KB）
        max_allowed = expected_length + max(expected_length * 0.01, 1024)
        if actual_size > max_allowed:
            return False

        return True
    except Exception:
        return False


class DownloadValidator:
    """
    校验下载目录：解析 playlist、统计 ts 文件、对比 Content-Length，
    输出 ValidationResult 并可选打印报告。
    """

    def __init__(self, directory: str) -> None:
        self._directory = str(Path(directory).resolve())

    def validate(self) -> ValidationResult | None:
        """
        执行校验。若目录无效或缺少 playlist 则打印错误并返回 None。
        否则返回 ValidationResult。
        """
        if not self._ensure_directory():
            return None

        playlist_path = Path(self._directory) / "playlist.txt"
        if not playlist_path.exists():
            logger.error(f"错误: 找不到playlist.txt文件: {playlist_path}")
            return None

        expected_segments = PlaylistParser.parse(playlist_path)
        content_lengths = ContentLengthLoader.load(self._directory)
        ts_files = self._collect_ts_files()

        file_sizes, total_size = self._compute_file_sizes(ts_files)
        missing = self._missing_filenames(expected_segments, ts_files)
        zero_size, incomplete = self._check_sizes(ts_files, file_sizes, content_lengths)
        failed_urls = self._build_failed_urls(
            expected_segments, missing, zero_size, incomplete
        )

        result = ValidationResult(
            directory=self._directory,
            expected_count=len(expected_segments),
            actual_count=len(ts_files),
            total_size=total_size,
            missing_files=missing,
            zero_size_files=zero_size,
            incomplete_files=incomplete,
            failed_urls=failed_urls,
        )
        return result

    def _ensure_directory(self) -> bool:
        if not Path(self._directory).is_dir():
            logger.error(f"错误: 目录不存在: {self._directory}")
            return False
        return True

    def _collect_ts_files(self) -> list[str]:
        files = []
        for p in Path(self._directory).iterdir():
            if p.suffix == ".ts" and p.is_file():
                files.append(p.name)
        return files

    def _compute_file_sizes(self, ts_files: list[str]) -> tuple[dict[str, int], int]:
        file_sizes: dict[str, int] = {}
        total = 0
        for name in ts_files:
            path = Path(self._directory) / name
            size = _get_file_size(str(path))
            file_sizes[name] = size
            total += size
        return file_sizes, total

    def _missing_filenames(
        self, expected_segments: list[SegmentInfo], ts_files: list[str]
    ) -> list[str]:
        expected_names = {seg.expected_filename for seg in expected_segments}
        actual_names = set(ts_files)
        return list(expected_names - actual_names)

    def _check_sizes(
        self,
        ts_files: list[str],
        file_sizes: dict[str, int],
        content_lengths: dict[str, int],
    ) -> tuple[list[str], list[str]]:
        zero_size: list[str] = []
        incomplete: list[str] = []
        for name in sorted(ts_files):
            path = str(Path(self._directory) / name)
            size = file_sizes[name]
            if size == 0:
                zero_size.append(name)
            elif name in content_lengths:
                if not _validate_content_length(path, content_lengths[name]):
                    incomplete.append(name)
        return zero_size, incomplete

    def _build_failed_urls(
        self,
        expected_segments: list[SegmentInfo],
        missing: list[str],
        zero_size: list[str],
        incomplete: list[str],
    ) -> dict[str, str]:
        filename_to_url = {seg.expected_filename: seg.url for seg in expected_segments}
        failed_set = set(missing) | set(zero_size) | set(incomplete)
        return {
            name: filename_to_url[name]
            for name in failed_set
            if name in filename_to_url
        }


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    val = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if val < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} TB"


def print_validation_report(result: ValidationResult) -> None:
    """显示统计信息与校验结论（原有打印逻辑）"""
    logger.info("文件统计:")
    logger.info(f"  预期文件数量: {result.expected_count}")
    logger.info(f"  实际文件数量: {result.actual_count}")

    if result.is_complete:
        logger.info("✅ 校验通过: 所有文件已完整下载")
    else:
        total_failed = len(result.failed_files)
        logger.error(f"❌ 校验失败: 发现 {total_failed} 个失败文件")
        logger.error("  失败文件类型统计:")
        logger.error(f"    - 缺失: {len(result.missing_files)} 个")
        logger.error(f"    - 空文件: {len(result.zero_size_files)} 个")
        logger.error(f"    - 不完整: {len(result.incomplete_files)} 个")

        failed_sorted = result.failed_files
        if failed_sorted:
            logger.error("  前十个失败的文件名:")
            for i, filename in enumerate(failed_sorted[:10], 1):
                logger.error(f"    {i}. {filename}")
            if len(failed_sorted) > 10:
                logger.error(f"    ... 还有 {len(failed_sorted) - 10} 个失败文件")
    logger.info("")


# ---------------------------------------------------------------------------
# 入口：兼容原有 validate_downloads(directory) 与 main()
# ---------------------------------------------------------------------------


def validate_downloads(directory: str) -> tuple[bool, dict]:
    """
    校验下载的文件（保留原有接口：返回 (is_complete, result_dict)）
    """
    validator = DownloadValidator(directory)
    result = validator.validate()
    if result is None:
        return False, {}

    print_validation_report(result)
    return result.is_complete, result.to_legacy_dict()


def main() -> None:
    """主函数"""
    if len(sys.argv) < 2:
        logger.error("用法: python validate_downloads.py <目录路径或视频名>")
        logger.error(
            "示例: python validate_downloads.py my_video   # 默认校验 movies/my_video"
        )
        logger.error("      python validate_downloads.py ./my_video")
        sys.exit(1)

    directory = _resolve_directory(sys.argv[1])
    is_complete, _result = validate_downloads(directory)
    sys.exit(0 if is_complete else 1)


if __name__ == "__main__":
    main()
