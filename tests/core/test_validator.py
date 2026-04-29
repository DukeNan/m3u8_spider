"""core/validator 单元测试"""

from __future__ import annotations

import json
from pathlib import Path

from m3u8_spider.core.validator import (
    ContentLengthLoader,
    DownloadValidator,
    PlaylistParser,
    ValidationResult,
    _validate_content_length,
    format_size,
)


class TestPlaylistParser:
    """PlaylistParser.parse() 测试"""

    def test_parse_normal_playlist(self, playlist_dir: Path) -> None:
        playlist_path = playlist_dir / "playlist.txt"
        segments = PlaylistParser.parse(str(playlist_path))
        assert len(segments) == 3
        assert segments[0].index == 0
        assert segments[0].expected_filename == "segment_00001.ts"
        assert segments[1].expected_filename == "segment_00002.ts"
        assert segments[2].expected_filename == "segment_00003.ts"

    def test_parse_relative_urls(self, playlist_dir: Path) -> None:
        """测试不含目录前缀的 URL，此时用 Path.name 取文件名"""
        playlist_path = playlist_dir / "playlist.txt"
        playlist_path.write_text(
            "#EXTM3U\n#EXTINF:10.0,\nsegment_00001.ts\n#EXTINF:10.0,\nsegment_00002.ts\n",
            encoding="utf-8",
        )
        segments = PlaylistParser.parse(str(playlist_path))
        assert len(segments) == 2
        assert segments[0].url == "segment_00001.ts"
        assert segments[0].expected_filename == "segment_00001.ts"

    def test_parse_empty_file_returns_empty(self, tmp_path: Path) -> None:
        playlist_path = tmp_path / "playlist.txt"
        playlist_path.write_text("", encoding="utf-8")
        segments = PlaylistParser.parse(str(playlist_path))
        assert segments == []

    def test_parse_file_not_found_returns_empty(self) -> None:
        segments = PlaylistParser.parse("/nonexistent/playlist.txt")
        assert segments == []

    def test_parse_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        playlist_path = tmp_path / "playlist.txt"
        playlist_path.write_text(
            "#EXTM3U\n#EXT-X-VERSION:3\n\n#EXTINF:10.0,\nhttps://example.com/seg1.ts\n\n",
            encoding="utf-8",
        )
        segments = PlaylistParser.parse(str(playlist_path))
        assert len(segments) == 1


class TestValidateContentLength:
    """_validate_content_length() 测试"""

    def test_exact_match(self) -> None:
        assert _validate_content_length(1000, 1000) is True

    def test_slightly_larger_within_tolerance(self) -> None:
        # 允许 max(1%, 1024) = 1024 余量
        assert _validate_content_length(2000, 1000) is True

    def test_below_expected(self) -> None:
        assert _validate_content_length(500, 1000) is False

    def test_exceeds_tolerance(self) -> None:
        max_allowed = 1000 + max(1000 * 0.01, 1024)
        assert _validate_content_length(int(max_allowed) + 1, 1000) is False

    def test_large_file_one_percent_tolerance(self) -> None:
        # 对于大文件使用 1% 余量
        assert _validate_content_length(1_010_000, 1_000_000) is True
        assert _validate_content_length(1_020_000, 1_000_000) is False


class TestValidationResult:
    """ValidationResult 属性测试"""

    def test_is_complete_when_all_match(self) -> None:
        result = ValidationResult(
            directory="/d",
            expected_count=3,
            actual_count=3,
            total_size=3000,
            missing_files=[],
            zero_size_files=[],
            incomplete_files=[],
        )
        assert result.is_complete is True

    def test_is_not_complete_when_count_mismatch(self) -> None:
        result = ValidationResult(
            directory="/d",
            expected_count=3,
            actual_count=2,
            total_size=2000,
            missing_files=["seg3.ts"],
            zero_size_files=[],
            incomplete_files=[],
        )
        assert result.is_complete is False

    def test_is_not_complete_with_zero_size(self) -> None:
        result = ValidationResult(
            directory="/d",
            expected_count=3,
            actual_count=3,
            total_size=2000,
            missing_files=[],
            zero_size_files=["seg2.ts"],
            incomplete_files=[],
        )
        assert result.is_complete is False

    def test_failed_files_dedup_and_sort(self) -> None:
        result = ValidationResult(
            directory="/d",
            expected_count=5,
            actual_count=3,
            total_size=3000,
            missing_files=["seg3.ts", "seg1.ts"],
            zero_size_files=["seg1.ts"],
            incomplete_files=["seg2.ts"],
        )
        assert result.failed_files == ["seg1.ts", "seg2.ts", "seg3.ts"]

    def test_to_legacy_dict(self) -> None:
        result = ValidationResult(
            directory="/d",
            expected_count=3,
            actual_count=2,
            total_size=2000,
            missing_files=["seg3.ts"],
            zero_size_files=[],
            incomplete_files=[],
            failed_urls={"seg3.ts": "https://example.com/seg3.ts"},
        )
        d = result.to_legacy_dict()
        assert d["is_complete"] is False
        assert d["missing_count"] == 1
        assert d["failed_urls"] == {"seg3.ts": "https://example.com/seg3.ts"}


class TestFormatSize:
    """format_size() 测试"""

    def test_bytes(self) -> None:
        assert format_size(500) == "500.00 B"

    def test_kilobytes(self) -> None:
        assert format_size(2048) == "2.00 KB"

    def test_megabytes(self) -> None:
        result = format_size(3_145_728)  # 3 MB
        assert "MB" in result

    def test_gigabytes(self) -> None:
        result = format_size(3_221_225_472)  # 3 GB
        assert "GB" in result

    def test_terabytes(self) -> None:
        result = format_size(3_221_225_472_000)  # ~3 TB
        assert "TB" in result

    def test_zero_bytes(self) -> None:
        assert format_size(0) == "0.00 B"


class TestContentLengthLoader:
    """ContentLengthLoader.load() 测试"""

    def test_load_existing_file(self, tmp_path: Path) -> None:
        lengths = {"seg1.ts": 1000, "seg2.ts": 2000}
        (tmp_path / "content_lengths.json").write_text(json.dumps(lengths), encoding="utf-8")

        result = ContentLengthLoader.load(str(tmp_path))
        assert result == {"seg1.ts": 1000, "seg2.ts": 2000}

    def test_file_not_exists_returns_empty(self, tmp_path: Path) -> None:
        result = ContentLengthLoader.load(str(tmp_path))
        assert result == {}

    def test_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "content_lengths.json").write_text("not json", encoding="utf-8")
        result = ContentLengthLoader.load(str(tmp_path))
        assert result == {}


class TestDownloadValidator:
    """DownloadValidator 集成测试（使用临时文件）"""

    def test_validate_complete_download(self, playlist_dir_with_content_lengths: Path) -> None:
        validator = DownloadValidator(str(playlist_dir_with_content_lengths))
        result = validator.validate()
        assert result is not None
        assert result.is_complete is True
        assert result.expected_count == 3
        assert result.actual_count == 3

    def test_validate_missing_files(self, playlist_dir: Path) -> None:
        """playlist 有 3 个片段但没有 ts 文件"""
        validator = DownloadValidator(str(playlist_dir))
        result = validator.validate()
        assert result is not None
        assert result.is_complete is False
        assert result.actual_count == 0
        assert len(result.missing_files) == 3

    def test_validate_partial_files(self, playlist_dir_with_ts: Path) -> None:
        """有 ts 文件但无 content_lengths"""
        validator = DownloadValidator(str(playlist_dir_with_ts))
        result = validator.validate()
        assert result is not None
        assert result.actual_count == 3
        # 没有 content_lengths，只检查零大小
        assert len(result.zero_size_files) == 0

    def test_validate_nonexistent_directory(self) -> None:
        validator = DownloadValidator("/nonexistent/directory")
        result = validator.validate()
        assert result is None

    def test_validate_with_zero_size_file(self, playlist_dir: Path) -> None:
        (playlist_dir / "segment_00001.ts").write_text("")
        validator = DownloadValidator(str(playlist_dir))
        result = validator.validate()
        assert result is not None
        assert result.is_complete is False
        assert "segment_00001.ts" in result.zero_size_files

    def test_validate_incomplete_file(self, playlist_dir_with_content_lengths: Path) -> None:
        """文件大小小于预期"""
        (playlist_dir_with_content_lengths / "segment_00001.ts").write_bytes(b"x" * 500)
        validator = DownloadValidator(str(playlist_dir_with_content_lengths))
        result = validator.validate()
        assert result is not None
        assert result.is_complete is False
        assert "segment_00001.ts" in result.incomplete_files
