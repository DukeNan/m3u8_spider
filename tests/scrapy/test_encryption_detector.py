"""Scrapy EncryptionDetector 单元测试"""

from __future__ import annotations

from m3u8_spider.spiders.m3u8_downloader import EncryptionDetector, EncryptionInfo


class TestEncryptionDetectorFromContent:
    """EncryptionDetector._from_content() 测试"""

    def test_detect_aes_128_encryption(self, m3u8_content_encrypted: str) -> None:
        result = EncryptionDetector._from_content(m3u8_content_encrypted)
        assert result.is_encrypted is True
        assert result.method == "AES-128"
        assert result.key_uri == "https://key.example.com/key"
        assert result.iv == "0xabc"

    def test_detect_no_encryption(self, m3u8_content_simple: str) -> None:
        result = EncryptionDetector._from_content(m3u8_content_simple)
        assert result.is_encrypted is False
        assert result.method is None

    def test_skips_none_key(self, m3u8_content_none_key: str) -> None:
        """第一个 METHOD=NONE 被跳过，第二个 AES-128 被检测"""
        result = EncryptionDetector._from_content(m3u8_content_none_key)
        assert result.is_encrypted is True
        assert result.method == "AES-128"
        assert result.key_uri == "https://key.example.com/key"


class TestEncryptionDetectorDetect:
    """EncryptionDetector.detect() 测试"""

    def test_detect_with_content_and_no_playlist(self, m3u8_content_encrypted: str) -> None:
        result = EncryptionDetector.detect(m3u8_content_encrypted, None)
        assert result.is_encrypted is True
        assert result.method == "AES-128"

    def test_detect_unencrypted(self, m3u8_content_simple: str) -> None:
        result = EncryptionDetector.detect(m3u8_content_simple, None)
        assert result.is_encrypted is False


class TestEncryptionInfoDefaults:
    """EncryptionInfo 默认值与工厂方法"""

    def test_default_unencrypted(self) -> None:
        info = EncryptionInfo.default_unencrypted()
        assert info.is_encrypted is False
        assert info.method is None
        assert info.key_uri is None
        assert info.key_file == "encryption.key"
        assert info.iv is None

    def test_to_dict_contains_all_fields(self) -> None:
        info = EncryptionInfo.default_unencrypted()
        d = info.to_dict()
        assert d["is_encrypted"] is False
        assert d["method"] is None
        assert d["key_file"] == "encryption.key"

    def test_to_dict_encrypted(self) -> None:
        info = EncryptionInfo(
            is_encrypted=True,
            method="AES-128",
            key_uri="https://example.com/key",
            key_file="encryption.key",
            iv="0xabc",
            keyformat=None,
            keyformatversions=None,
        )
        d = info.to_dict()
        assert d["is_encrypted"] is True
        assert d["method"] == "AES-128"
        assert d["iv"] == "0xabc"

    def test_construction_with_all_fields(self) -> None:
        info = EncryptionInfo(
            is_encrypted=True,
            method="SAMPLE-AES",
            key_uri="https://key.url",
            key_file="custom.key",
            iv="0x123",
            keyformat="identity",
            keyformatversions="1",
        )
        assert info.method == "SAMPLE-AES"
        assert info.keyformat == "identity"
        assert info.keyformatversions == "1"
