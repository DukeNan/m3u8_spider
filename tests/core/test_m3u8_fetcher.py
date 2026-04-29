"""core/m3u8_fetcher 单元测试"""

from __future__ import annotations

from m3u8_spider.core.m3u8_fetcher import find_m3u8_url


class TestFindM3U8Url:
    """find_m3u8_url() 正则匹配测试"""

    def test_match_https_url(self) -> None:
        html = '<video src="https://example.com/playlist.m3u8"></video>'
        result = find_m3u8_url(html)
        assert result == "https://example.com/playlist.m3u8"

    def test_match_relative_path(self) -> None:
        html = '<video src="/path/to/playlist.m3u8"></video>'
        result = find_m3u8_url(html)
        assert result == "/path/to/playlist.m3u8"

    def test_match_url_with_query_string(self) -> None:
        html = '<video src="https://example.com/playlist.m3u8?token=abc&exp=123"></video>'
        result = find_m3u8_url(html)
        assert "token=abc" in result

    def test_return_first_match(self) -> None:
        html = (
            '<video src="https://example.com/first.m3u8"></video>'
            '<video src="https://example.com/second.m3u8"></video>'
        )
        result = find_m3u8_url(html)
        assert result == "https://example.com/first.m3u8"

    def test_no_match_returns_none(self) -> None:
        html = "<html><body>No video here</body></html>"
        result = find_m3u8_url(html)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = find_m3u8_url("")
        assert result is None

    def test_match_url_with_single_quotes(self) -> None:
        html = "<source src='https://example.com/playlist.m3u8'>"
        result = find_m3u8_url(html)
        assert result == "https://example.com/playlist.m3u8"
