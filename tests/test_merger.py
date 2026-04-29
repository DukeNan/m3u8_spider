"""utils/merger 纯函数单元测试"""

from __future__ import annotations

import json
from pathlib import Path

from m3u8_spider.utils.merger import (
    EncryptionInfo,
    TSFileCollector,
    _create_file_list,
    _create_temp_m3u8,
    _ts_sort_key,
)


class TestTSSortKey:
    """_ts_sort_key() 排序键测试"""

    def test_numbers_only_filename(self) -> None:
        key = _ts_sort_key("/path/segment_00001.ts")
        assert key[0] == 0  # has-number bucket
        assert key[1] == (1,)  # extracted numbers

    def test_multiple_number_groups(self) -> None:
        key = _ts_sort_key("/path/video_123_part_456.ts")
        assert key[0] == 0
        assert key[1] == (123, 456)

    def test_no_numbers_filename(self) -> None:
        key = _ts_sort_key("/path/video.ts")
        assert key[0] == 1  # fallback bucket
        assert key[2] == "video.ts"

    def test_sort_order(self) -> None:
        files = [
            "/path/segment_2.ts",
            "/path/segment_10.ts",
            "/path/segment_1.ts",
        ]
        sorted_files = sorted(files, key=_ts_sort_key)
        assert sorted_files == [
            "/path/segment_1.ts",
            "/path/segment_2.ts",
            "/path/segment_10.ts",
        ]


class TestEncryptionInfoFromDirectory:
    """EncryptionInfo.from_directory() 测试"""

    def test_loads_encrypted_info(self, tmp_path: Path) -> None:
        info = {"is_encrypted": True, "method": "AES-128", "key_file": "custom.key", "iv": None}
        (tmp_path / "encryption_info.json").write_text(json.dumps(info), encoding="utf-8")

        result = EncryptionInfo.from_directory(str(tmp_path))
        assert result is not None
        assert result.is_encrypted is True
        assert result.method == "AES-128"
        assert result.key_file == "custom.key"

    def test_loads_unencrypted_info(self, tmp_path: Path) -> None:
        info = {"is_encrypted": False, "method": "AES-128", "key_file": "encryption.key", "iv": None}
        (tmp_path / "encryption_info.json").write_text(json.dumps(info), encoding="utf-8")

        result = EncryptionInfo.from_directory(str(tmp_path))
        assert result is not None
        assert result.is_encrypted is False

    def test_file_not_exists_returns_none(self, tmp_path: Path) -> None:
        result = EncryptionInfo.from_directory(str(tmp_path))
        assert result is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "encryption_info.json").write_text("not-json", encoding="utf-8")
        result = EncryptionInfo.from_directory(str(tmp_path))
        assert result is None

    def test_empty_directory_returns_none(self, tmp_path: Path) -> None:
        result = EncryptionInfo.from_directory(str(tmp_path))
        assert result is None


class TestCreateFileList:
    """_create_file_list() 测试"""

    def test_creates_correct_format(self, tmp_path: Path) -> None:
        ts_files = [str(tmp_path / "seg1.ts"), str(tmp_path / "seg2.ts")]
        (tmp_path / "seg1.ts").write_text("dummy")
        (tmp_path / "seg2.ts").write_text("dummy")

        list_path = _create_file_list(ts_files, "file_list.txt")
        content = Path(list_path).read_text(encoding="utf-8")

        assert f"file '{tmp_path}/seg1.ts'" in content
        assert f"file '{tmp_path}/seg2.ts'" in content

    def test_escapes_single_quotes(self, tmp_path: Path) -> None:
        ts_files = [str(tmp_path / "seg'1.ts")]
        (tmp_path / "seg'1.ts").write_text("dummy")

        list_path = _create_file_list(ts_files, "file_list.txt")
        content = Path(list_path).read_text(encoding="utf-8")

        assert "\\'" in content


class TestCreateTempM3U8:
    """_create_temp_m3u8() 测试"""

    def test_unencrypted(self, tmp_path: Path) -> None:
        ts_files = [str(tmp_path / "seg1.ts"), str(tmp_path / "seg2.ts")]
        result = _create_temp_m3u8(str(tmp_path), ts_files, None)

        content = Path(result).read_text(encoding="utf-8")
        assert "#EXTM3U" in content
        assert "#EXT-X-ENDLIST" in content
        assert "#EXT-X-KEY" not in content

    def test_encrypted(self, tmp_path: Path) -> None:
        ts_files = [str(tmp_path / "seg1.ts")]
        enc = EncryptionInfo(is_encrypted=True, method="AES-128", key_file="keyfile.key", iv="0x123")

        result = _create_temp_m3u8(str(tmp_path), ts_files, enc)
        content = Path(result).read_text(encoding="utf-8")

        assert "#EXT-X-KEY:METHOD=AES-128" in content
        assert "IV=0x123" in content

    def test_encrypted_no_iv(self, tmp_path: Path) -> None:
        ts_files = [str(tmp_path / "seg1.ts")]
        enc = EncryptionInfo(is_encrypted=True, method="AES-128", key_file="keyfile.key", iv=None)

        result = _create_temp_m3u8(str(tmp_path), ts_files, enc)
        content = Path(result).read_text(encoding="utf-8")

        assert "#EXT-X-KEY:METHOD=AES-128" in content
        assert "IV=" not in content.rsplit("#EXT-X-KEY", 1)[-1].split("\n")[0]


class TestTSFileCollector:
    """TSFileCollector.collect() 测试"""

    def test_collects_ts_files_sorted(self, tmp_path: Path) -> None:
        files = ["seg_2.ts", "seg_10.ts", "seg_1.ts"]
        for f in files:
            (tmp_path / f).write_text("dummy")

        result = TSFileCollector.collect(str(tmp_path))
        names = [Path(p).name for p in result]
        assert names == ["seg_1.ts", "seg_2.ts", "seg_10.ts"]

    def test_ignores_non_ts_files(self, tmp_path: Path) -> None:
        (tmp_path / "seg1.ts").write_text("dummy")
        (tmp_path / "readme.txt").write_text("dummy")
        (tmp_path / "playlist.txt").write_text("dummy")

        result = TSFileCollector.collect(str(tmp_path))
        assert len(result) == 1
        assert "seg1.ts" in result[0]

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        result = TSFileCollector.collect(str(tmp_path))
        assert result == []

    def test_nonexistent_directory_returns_empty_list(self) -> None:
        result = TSFileCollector.collect("/nonexistent/path")
        assert result == []
