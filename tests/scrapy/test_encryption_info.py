"""Scrapy spider 内 EncryptionInfo dataclass 单元测试"""

from __future__ import annotations

from m3u8_spider.spiders.m3u8_downloader import EncryptionInfo


class TestEncryptionInfo:
    """EncryptionInfo dataclass 测试"""

    def test_encrypted_instance(self) -> None:
        info = EncryptionInfo(
            is_encrypted=True,
            method="AES-128",
            key_uri="https://example.com/key",
            key_file="encryption.key",
            iv="0x123",
            keyformat=None,
            keyformatversions=None,
        )
        assert info.is_encrypted is True
        assert info.method == "AES-128"
        assert info.key_uri == "https://example.com/key"

    def test_to_dict_returns_all_fields(self) -> None:
        info = EncryptionInfo(
            is_encrypted=True,
            method="AES-128",
            key_uri="https://example.com/key",
            key_file="custom.key",
            iv="0xabc",
            keyformat="identity",
            keyformatversions="1",
        )
        d = info.to_dict()
        assert d["is_encrypted"] is True
        assert d["method"] == "AES-128"
        assert d["key_uri"] == "https://example.com/key"
        assert d["key_file"] == "custom.key"
        assert d["iv"] == "0xabc"
        assert d["keyformat"] == "identity"
        assert d["keyformatversions"] == "1"

    def test_default_unencrypted(self) -> None:
        info = EncryptionInfo.default_unencrypted()
        assert info.is_encrypted is False
        assert info.method is None
        assert info.key_uri is None
        assert info.key_file == "encryption.key"
        assert info.iv is None
        assert info.keyformat is None
        assert info.keyformatversions is None

    def test_default_unencrypted_to_dict(self) -> None:
        info = EncryptionInfo.default_unencrypted()
        d = info.to_dict()
        assert d["is_encrypted"] is False
        assert d["method"] is None
        assert d["key_file"] == "encryption.key"
