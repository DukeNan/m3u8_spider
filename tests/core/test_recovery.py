"""core/recovery 纯函数单元测试"""

from __future__ import annotations

from m3u8_spider.core.recovery import _build_retry_urls, _extract_failed_urls, _requires_encryption_key


class TestRequiresEncryptionKey:
    """_requires_encryption_key() 测试"""

    def test_encrypted_with_key_uri_returns_true(self) -> None:
        assert _requires_encryption_key({"is_encrypted": True, "key_uri": "https://key.url"}) is True

    def test_encrypted_no_key_uri_returns_false(self) -> None:
        assert _requires_encryption_key({"is_encrypted": True, "key_uri": None}) is False

    def test_not_encrypted_returns_false(self) -> None:
        assert _requires_encryption_key({"is_encrypted": False, "key_uri": "https://key.url"}) is False

    def test_empty_dict_returns_false(self) -> None:
        assert _requires_encryption_key({}) is False


class TestExtractFailedUrls:
    """_extract_failed_urls() 测试"""

    def test_extracts_valid_urls(self) -> None:
        result = _extract_failed_urls(
            {"failed_urls": {"seg1.ts": "https://example.com/seg1.ts", "seg2.ts": ""}}
        )
        # 空 URL 会被过滤
        assert result == {"seg1.ts": "https://example.com/seg1.ts"}

    def test_empty_failed_urls_returns_empty(self) -> None:
        result = _extract_failed_urls({"failed_urls": {}})
        assert result == {}

    def test_missing_failed_urls_returns_empty(self) -> None:
        result = _extract_failed_urls({"other": "data"})
        assert result == {}

    def test_not_dict_returns_empty(self) -> None:
        result = _extract_failed_urls("not a dict")
        assert result == {}

    def test_failed_urls_not_dict_returns_empty(self) -> None:
        result = _extract_failed_urls({"failed_urls": "not a dict"})
        assert result == {}

    def test_ensures_str_types(self) -> None:
        result = _extract_failed_urls({"failed_urls": {1: 2}})
        assert result == {"1": "2"}


class TestBuildRetryUrls:
    """_build_retry_urls() 测试"""

    def test_builds_sorted_retry_list(self) -> None:
        result = _build_retry_urls(
            {"seg2.ts": "https://example.com/seg2.ts", "seg1.ts": "https://example.com/seg1.ts"}
        )
        assert result == [
            {"url": "https://example.com/seg1.ts", "filename": "seg1.ts"},
            {"url": "https://example.com/seg2.ts", "filename": "seg2.ts"},
        ]

    def test_empty_dict_returns_empty_list(self) -> None:
        result = _build_retry_urls({})
        assert result == []
