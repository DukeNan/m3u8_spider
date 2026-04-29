"""core/downloader 单元测试"""

from __future__ import annotations

import pytest

from m3u8_spider.core.downloader import DownloadConfig


class TestDownloadConfigPostInit:
    """DownloadConfig.__post_init__() 验证逻辑"""

    def test_valid_url_and_filename(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/playlist.m3u8", filename="my_video")
        assert config.m3u8_url == "https://example.com/playlist.m3u8"
        assert config.filename == "my_video"

    def test_http_url_accepted(self) -> None:
        config = DownloadConfig(m3u8_url="http://example.com/playlist.m3u8", filename="my_video")
        assert config.m3u8_url == "http://example.com/playlist.m3u8"

    def test_invalid_url_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="无效的URL"):
            DownloadConfig(m3u8_url="ftp://example.com/file", filename="my_video")

    def test_empty_filename_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="文件名不能为空"):
            DownloadConfig(m3u8_url="https://example.com/playlist.m3u8", filename="")

    def test_blank_filename_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="文件名不能为空"):
            DownloadConfig(m3u8_url="https://example.com/playlist.m3u8", filename="   ")

    def test_metadata_only_and_retry_urls_mutually_exclusive(self) -> None:
        with pytest.raises(ValueError, match="metadata_only 与 retry_urls 不能同时启用"):
            DownloadConfig(
                m3u8_url="https://example.com/playlist.m3u8",
                filename="my_video",
                metadata_only=True,
                retry_urls=[{"url": "https://example.com/seg.ts", "filename": "seg.ts"}],
            )


class TestDownloadConfigSanitizedFilename:
    """sanitized_filename 属性测试"""

    def test_normal_filename_unchanged(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="my_video")
        assert config.sanitized_filename == "my_video"

    def test_replaces_invalid_chars(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename='my:video<name>"')
        assert config.sanitized_filename == "my_video_name__"

    def test_strips_whitespace(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="  my_video  ")
        assert config.sanitized_filename == "my_video"

    def test_all_invalid_chars_replaced(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename='<>:"/\\|?*')
        assert config.sanitized_filename == "_________"


class TestDownloadConfigProperties:
    """DownloadConfig 路径属性测试"""

    def test_project_root_is_absolute(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="test")
        assert config.project_root.is_absolute()

    def test_scrapy_project_dir_ends_with_scrapy_project(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="test")
        assert config.scrapy_project_dir.name == "scrapy_project"

    def test_download_dir_ends_with_movies_filename(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="my_video")
        parts = config.download_dir.parts
        assert "movies" in parts
        assert parts[-1] == "my_video"

    def test_default_concurrent_is_32(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="test")
        assert config.concurrent == 32

    def test_default_delay_is_zero(self) -> None:
        config = DownloadConfig(m3u8_url="https://example.com/p.m3u8", filename="test")
        assert config.delay == 0.0
