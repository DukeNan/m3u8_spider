"""Scrapy UrlResolver 单元测试"""

from __future__ import annotations

from m3u8_spider.spiders.m3u8_downloader import UrlResolver


class TestUrlResolver:
    """UrlResolver.resolve() 测试"""

    def test_absolute_url_returned_as_is(self) -> None:
        resolver = UrlResolver("https://example.com", "/playlist.m3u8")
        assert resolver.resolve("https://other.com/seg.ts") == "https://other.com/seg.ts"

    def test_empty_uri_returns_empty(self) -> None:
        resolver = UrlResolver("https://example.com", "/playlist.m3u8")
        assert resolver.resolve("") == ""

    def test_root_relative_path(self) -> None:
        resolver = UrlResolver("http://example.com", "/playlist.m3u8")
        result = resolver.resolve("/segments/seg1.ts")
        assert result == "http://example.com/segments/seg1.ts"

    def test_relative_to_m3u8_path(self) -> None:
        resolver = UrlResolver("https://example.com", "/videos/playlist.m3u8")
        result = resolver.resolve("seg1.ts")
        assert result == "https://example.com/videos/seg1.ts"

    def test_relative_path_with_subdirectory(self) -> None:
        resolver = UrlResolver("https://example.com", "/videos/hls/playlist.m3u8")
        result = resolver.resolve("sub/seg1.ts")
        assert result == "https://example.com/videos/hls/sub/seg1.ts"

    def test_base_url_with_trailing_slash(self) -> None:
        resolver = UrlResolver("https://example.com/", "/playlist.m3u8")
        result = resolver.resolve("/seg1.ts")
        assert result == "https://example.com/seg1.ts"

    def test_m3u8_at_root_path(self) -> None:
        resolver = UrlResolver("https://example.com", "/playlist.m3u8")
        result = resolver.resolve("seg1.ts")
        assert result == "https://example.com/seg1.ts"

    def test_base_url_with_path(self) -> None:
        resolver = UrlResolver("https://example.com/videos", "/playlist.m3u8")
        result = resolver.resolve("seg1.ts")
        assert result == "https://example.com/videos/seg1.ts"
