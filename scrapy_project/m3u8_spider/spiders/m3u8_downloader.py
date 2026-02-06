"""
M3U8 下载爬虫：下载并解析 M3U8 播放列表，产出 TS 片段与密钥下载项。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import m3u8
import scrapy
from scrapy.http import Request

from m3u8_spider.items import M3U8Item


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

PLAYLIST_FILENAME = "playlist.txt"
ENCRYPTION_INFO_FILENAME = "encryption_info.json"
DEFAULT_KEY_FILENAME = "encryption.key"

# 加密检测正则
KEY_LINE_PATTERN = re.compile(r"#EXT-X-KEY:(.+)")
METHOD_PATTERN = re.compile(r"METHOD=([^,\s]+)")
URI_PATTERN = re.compile(r'URI="([^"]+)"')
IV_PATTERN = re.compile(r"IV=(0x[0-9A-Fa-f]+)")
KEYFORMAT_PATTERN = re.compile(r'KEYFORMAT="([^"]+)"')
KEYFORMATVERSIONS_PATTERN = re.compile(r'KEYFORMATVERSIONS="([^"]+)"')


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class EncryptionInfo:
    """M3U8 加密检测结果（与 encryption_info.json 结构一致）"""

    is_encrypted: bool
    method: str | None
    key_uri: str | None
    key_file: str
    iv: str | None
    keyformat: str | None
    keyformatversions: str | None

    def to_dict(self) -> dict:
        """序列化为 JSON 可写字典"""
        return {
            "is_encrypted": self.is_encrypted,
            "method": self.method,
            "key_uri": self.key_uri,
            "key_file": self.key_file,
            "iv": self.iv,
            "keyformat": self.keyformat,
            "keyformatversions": self.keyformatversions,
        }

    @classmethod
    def default_unencrypted(cls) -> EncryptionInfo:
        """未加密时的默认信息"""
        return cls(
            is_encrypted=False,
            method=None,
            key_uri=None,
            key_file=DEFAULT_KEY_FILENAME,
            iv=None,
            keyformat=None,
            keyformatversions=None,
        )


# ---------------------------------------------------------------------------
# URL 解析（单一职责：相对/绝对 URL → 绝对 URL）
# ---------------------------------------------------------------------------


class UrlResolver:
    """
    将 M3U8 中的相对 URI 解析为绝对 URL。
    依赖 base_url 与 m3u8 路径（用于非根相对路径）。
    """

    def __init__(self, base_url: str, m3u8_path: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._base_path = os.path.dirname(urlparse(m3u8_path).path) or ""

    def resolve(self, uri: str) -> str:
        """
        将片段或密钥 URI 转为绝对 URL。
        若已是 http(s) 则原样返回；否则按 / 开头或相对路径拼接。
        """
        if not uri or uri.startswith("http"):
            return uri or ""

        if uri.startswith("/"):
            return urljoin(f"{self._base_url}/", uri)

        # 相对于 m3u8 所在目录
        if self._base_path:
            base_with_slash = f"{self._base_url}{self._base_path}/"
        else:
            base_with_slash = f"{self._base_url}/"
        return urljoin(base_with_slash, uri)


# ---------------------------------------------------------------------------
# 加密检测（单一职责：从内容或 playlist 对象检测加密）
# ---------------------------------------------------------------------------


class EncryptionDetector:
    """从 M3U8 文本或 m3u8 库的 playlist 对象检测加密信息"""

    @classmethod
    def detect(cls, m3u8_content: str, playlist: object | None = None) -> EncryptionInfo:
        """
        检测 m3u8 是否加密。

        Args:
            m3u8_content: M3U8 文件内容（字符串）
            playlist: m3u8 库解析的 playlist 对象（可选）

        Returns:
            加密信息
        """
        # 方法1: 使用 m3u8 库的 keys 属性
        if playlist and hasattr(playlist, "keys") and playlist.keys:
            info = cls._from_playlist_keys(playlist)
            if info:
                return info

        # 方法2: 手动解析 #EXT-X-KEY（备用）
        return cls._from_content(m3u8_content)

    @classmethod
    def _from_playlist_keys(cls, playlist: object) -> EncryptionInfo | None:
        """从 playlist.keys 提取第一个加密密钥信息"""
        for key in playlist.keys:
            if not key or not key.method or key.method.upper() == "NONE":
                continue
            return EncryptionInfo(
                is_encrypted=True,
                method=key.method,
                key_uri=key.uri,
                key_file=DEFAULT_KEY_FILENAME,
                iv=key.iv,
                keyformat=getattr(key, "keyformat", None),
                keyformatversions=getattr(key, "keyformatversions", None),
            )
        return None

    @classmethod
    def _from_content(cls, m3u8_content: str) -> EncryptionInfo:
        """从 M3U8 文本中正则匹配 #EXT-X-KEY"""
        result = EncryptionInfo.default_unencrypted()
        key_matches = KEY_LINE_PATTERN.findall(m3u8_content)

        for key_line in key_matches:
            method_match = METHOD_PATTERN.search(key_line)
            if not method_match:
                continue
            method = method_match.group(1).strip('"')
            if method.upper() == "NONE":
                continue

            uri_m = URI_PATTERN.search(key_line)
            iv_m = IV_PATTERN.search(key_line)
            kf_m = KEYFORMAT_PATTERN.search(key_line)
            kfv_m = KEYFORMATVERSIONS_PATTERN.search(key_line)
            result = EncryptionInfo(
                is_encrypted=True,
                method=method,
                key_uri=uri_m.group(1) if uri_m else None,
                key_file=DEFAULT_KEY_FILENAME,
                iv=iv_m.group(1) if iv_m else None,
                keyformat=kf_m.group(1) if kf_m else None,
                keyformatversions=kfv_m.group(1) if kfv_m else None,
            )
            break
        return result


# ---------------------------------------------------------------------------
# 爬虫
# ---------------------------------------------------------------------------


class M3U8DownloaderSpider(scrapy.Spider):
    """M3U8 文件下载爬虫：请求 M3U8 → 解析片段与加密 → 产出 TS 与密钥下载项。"""

    name = "m3u8_downloader"
    allowed_domains = []

    def __init__(
        self,
        m3u8_url: str | None = None,
        filename: str | None = None,
        retry_urls: list[dict] | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not m3u8_url:
            raise ValueError("必须提供m3u8_url参数")
        if not filename:
            raise ValueError("必须提供filename参数")

        self._m3u8_url = m3u8_url
        self._filename = filename
        self._retry_urls = retry_urls  # 重试模式：仅下载指定 URL 列表

        # 创建下载目录（相对于项目根目录；项目根 = scrapy_project 的父目录）
        project_root = self._project_root()
        self.download_directory = os.path.join(project_root, filename)
        os.makedirs(self.download_directory, exist_ok=True)

        parsed = urlparse(m3u8_url)
        self._base_url = f"{parsed.scheme}://{parsed.netloc}"
        self._base_path = os.path.dirname(parsed.path) or ""
        self._url_resolver = UrlResolver(self._base_url, parsed.path)

        if retry_urls:
            self.logger.info(f"重试模式: 将重新下载 {len(retry_urls)} 个文件")
        else:
            self.logger.info(f"M3U8 URL: {self._m3u8_url}")
        self.logger.info(f"下载目录: {self.download_directory}")

    @staticmethod
    def _project_root() -> str:
        """当前项目根目录（main.py 所在层级）"""
        current_dir = os.getcwd()
        if current_dir.endswith("scrapy_project"):
            return os.path.dirname(current_dir)
        return current_dir

    def start_requests(self):
        """首轮请求：重试模式直接产出片段项，否则请求 M3U8 地址。"""
        if self._retry_urls:
            yield from self._yield_retry_items()
        else:
            yield Request(
                url=self._m3u8_url,
                callback=self.parse_m3u8,
                dont_filter=True,
            )

    def _yield_retry_items(self):
        """重试模式：按 retry_urls 直接产出 M3U8Item。"""
        for url_info in self._retry_urls:
            item = M3U8Item()
            item["url"] = url_info["url"]
            item["filename"] = url_info["filename"]
            item["directory"] = self.download_directory
            item["segment_index"] = url_info.get("index", 0)
            yield item

    def parse_m3u8(self, response):
        """解析 M3U8 响应：保存 playlist、检测加密、写出加密信息、按需请求密钥、产出片段项。"""
        self._save_playlist(response.text)
        try:
            playlist = m3u8.loads(response.text, uri=self._m3u8_url)
            encryption_info = EncryptionDetector.detect(response.text, playlist)
            self._save_encryption_info(encryption_info)
            self._log_encryption(encryption_info)
            yield from self._yield_key_request_if_needed(encryption_info)
            yield from self._yield_segment_items_from_playlist(playlist)
        except Exception as e:
            self.logger.error(f"解析M3U8文件失败: {e}")
            # m3u8 库解析失败时回退到手动解析
            yield from self._parse_m3u8_manual(response.text)

    def _save_playlist(self, content: str) -> None:
        """将 M3U8 内容保存为 playlist.txt"""
        path = os.path.join(self.download_directory, PLAYLIST_FILENAME)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.logger.info(f"M3U8文件已保存到: {path}")

    def _save_encryption_info(self, info: EncryptionInfo) -> None:
        """将加密信息写入 encryption_info.json"""
        path = os.path.join(self.download_directory, ENCRYPTION_INFO_FILENAME)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(info.to_dict(), f, indent=2, ensure_ascii=False)

    def _log_encryption(self, info: EncryptionInfo) -> None:
        """根据加密状态打日志"""
        if info.is_encrypted:
            self.logger.info(
                f"⚠️  检测到加密: {info.method}, 密钥URI: {info.key_uri}"
            )
        else:
            self.logger.info("✅ 未检测到加密，m3u8文件为非加密格式")

    def _yield_key_request_if_needed(self, info: EncryptionInfo):
        """若加密且存在 key_uri，产出下载密钥的 Request。"""
        if not info.is_encrypted or not info.key_uri:
            return
        key_url = self._url_resolver.resolve(info.key_uri)
        self.logger.info(f"正在下载密钥文件: {key_url}")
        yield Request(
            url=key_url,
            callback=self._save_encryption_key,
            dont_filter=True,
        )

    def _save_encryption_key(self, response):
        """保存加密密钥文件"""
        key_path = os.path.join(self.download_directory, DEFAULT_KEY_FILENAME)
        with open(key_path, "wb") as f:
            f.write(response.body)
        self.logger.info(f"密钥文件已保存到: {key_path}")

    def _yield_segment_items_from_playlist(self, playlist):
        """从 m3u8 库的 playlist.segments 产出 M3U8Item。"""
        segments = getattr(playlist, "segments", None) or []
        self.logger.info(f"找到 {len(segments)} 个视频片段")
        for index, segment in enumerate(segments):
            segment_url = self._url_resolver.resolve(segment.uri)
            filename = self._segment_filename(segment.uri, index)
            yield self._build_item(segment_url, filename, index)

    def _segment_filename(self, segment_uri: str, index: int) -> str:
        """根据片段 URI 或索引生成保存文件名"""
        name = os.path.basename(segment_uri)
        if name and name.endswith(".ts"):
            return name
        return f"segment_{index:05d}.ts"

    def _build_item(self, url: str, filename: str, segment_index: int) -> M3U8Item:
        """构造单个 M3U8Item"""
        item = M3U8Item()
        item["url"] = url
        item["filename"] = filename
        item["directory"] = self.download_directory
        item["segment_index"] = segment_index
        return item

    def _parse_m3u8_manual(self, m3u8_content: str):
        """手动解析 M3U8 内容（备用）：加密信息 + 按行解析片段 URL，产出项与密钥请求。"""
        encryption_info = EncryptionDetector.detect(m3u8_content, None)
        self._save_encryption_info(encryption_info)
        self._log_encryption(encryption_info)
        yield from self._yield_key_request_if_needed(encryption_info)

        segment_index = 0
        for line in m3u8_content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 视为片段行（URL）
            if line.startswith("http"):
                segment_url = line
            else:
                segment_url = self._url_resolver.resolve(line)
            filename = os.path.basename(segment_url)
            if not filename or not filename.endswith(".ts"):
                filename = f"segment_{segment_index:05d}.ts"
            yield self._build_item(segment_url, filename, segment_index)
            segment_index += 1
