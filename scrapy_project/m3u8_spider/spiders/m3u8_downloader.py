import os
import json
import re
from urllib.parse import urljoin, urlparse
import scrapy
import m3u8
from scrapy.http import Request
from m3u8_spider.items import M3U8Item


class M3U8DownloaderSpider(scrapy.Spider):
    """M3U8文件下载爬虫"""

    name = "m3u8_downloader"
    allowed_domains = []

    def __init__(self, m3u8_url=None, filename=None, retry_urls=None, *args, **kwargs):
        super(M3U8DownloaderSpider, self).__init__(*args, **kwargs)
        if not m3u8_url:
            raise ValueError("必须提供m3u8_url参数")
        if not filename:
            raise ValueError("必须提供filename参数")

        self.m3u8_url = m3u8_url
        self.filename = filename
        self.retry_urls = retry_urls  # 重试模式：仅下载指定URL列表

        # 创建下载目录（相对于项目根目录）
        # 获取项目根目录（scrapy_project的父目录）
        current_dir = os.getcwd()
        if current_dir.endswith("scrapy_project"):
            project_root = os.path.dirname(current_dir)
        else:
            project_root = current_dir
        self.download_directory = os.path.join(project_root, filename)
        os.makedirs(self.download_directory, exist_ok=True)

        # 解析m3u8 URL的基础URL
        parsed = urlparse(m3u8_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.base_path = os.path.dirname(parsed.path) or ""

        if self.retry_urls:
            self.logger.info(f"重试模式: 将重新下载 {len(self.retry_urls)} 个文件")
        else:
            self.logger.info(f"M3U8 URL: {self.m3u8_url}")
        self.logger.info(f"下载目录: {self.download_directory}")

    def start_requests(self):
        """开始请求，首先下载m3u8文件"""
        # 如果是重试模式，直接下载指定的URL
        if self.retry_urls:
            for url_info in self.retry_urls:
                url = url_info["url"]
                filename = url_info["filename"]
                index = url_info.get("index", 0)

                # 创建item
                item = M3U8Item()
                item["url"] = url
                item["filename"] = filename
                item["directory"] = self.download_directory
                item["segment_index"] = index

                yield item
        else:
            # 正常模式，下载m3u8文件并解析
            yield Request(url=self.m3u8_url, callback=self.parse_m3u8, dont_filter=True)

    def parse_m3u8(self, response):
        """解析m3u8文件"""
        # 保存m3u8文件内容到playlist.txt
        playlist_path = os.path.join(self.download_directory, "playlist.txt")
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        self.logger.info(f"M3U8文件已保存到: {playlist_path}")

        # 解析m3u8内容
        try:
            # 使用m3u8库解析
            playlist = m3u8.loads(response.text, uri=self.m3u8_url)

            # 检测加密
            encryption_info = self._detect_encryption(response.text, playlist)

            # 保存加密信息
            encryption_info_path = os.path.join(
                self.download_directory, "encryption_info.json"
            )
            with open(encryption_info_path, "w", encoding="utf-8") as f:
                json.dump(encryption_info, f, indent=2, ensure_ascii=False)

            # 输出加密状态
            if encryption_info["is_encrypted"]:
                self.logger.info(
                    f"⚠️  检测到加密: {encryption_info['method']}, "
                    f"密钥URI: {encryption_info['key_uri']}"
                )

                # 下载密钥文件
                if encryption_info["key_uri"]:
                    key_url = encryption_info["key_uri"]
                    # 处理相对URL
                    if not key_url.startswith("http"):
                        if key_url.startswith("/"):
                            key_url = urljoin(self.base_url, key_url)
                        else:
                            base_dir = os.path.dirname(urlparse(self.m3u8_url).path)
                            if base_dir:
                                key_url = urljoin(f"{self.base_url}{base_dir}/", key_url)
                            else:
                                key_url = urljoin(f"{self.base_url}/", key_url)

                    self.logger.info(f"正在下载密钥文件: {key_url}")
                    # 下载密钥文件
                    yield Request(
                        url=key_url,
                        callback=self._save_encryption_key,
                        dont_filter=True,
                    )
            else:
                self.logger.info("✅ 未检测到加密，m3u8文件为非加密格式")

            # 获取所有片段
            segments = playlist.segments
            self.logger.info(f"找到 {len(segments)} 个视频片段")

            # 生成下载请求
            for index, segment in enumerate(segments):
                # 构建完整的URL
                segment_url = segment.uri
                if not segment_url.startswith("http"):
                    # 相对URL，需要拼接
                    if segment_url.startswith("/"):
                        segment_url = urljoin(self.base_url, segment_url)
                    else:
                        # 相对于m3u8文件的路径
                        base_dir = os.path.dirname(urlparse(self.m3u8_url).path)
                        if base_dir:
                            segment_url = urljoin(
                                f"{self.base_url}{base_dir}/", segment_url
                            )
                        else:
                            segment_url = urljoin(f"{self.base_url}/", segment_url)

                # 生成文件名
                segment_filename = os.path.basename(segment_url)
                if not segment_filename or not segment_filename.endswith(".ts"):
                    # 如果没有文件名或不是.ts，使用索引命名
                    segment_filename = f"segment_{index:05d}.ts"

                # 创建item
                item = M3U8Item()
                item["url"] = segment_url
                item["filename"] = segment_filename
                item["directory"] = self.download_directory
                item["segment_index"] = index

                yield item

        except Exception as e:
            self.logger.error(f"解析M3U8文件失败: {e}")
            # 如果m3u8库解析失败，尝试手动解析
            for item in self._parse_m3u8_manual(response.text):
                yield item

    def _save_encryption_key(self, response):
        """保存加密密钥文件"""
        key_path = os.path.join(self.download_directory, "encryption.key")
        with open(key_path, "wb") as f:
            f.write(response.body)
        self.logger.info(f"密钥文件已保存到: {key_path}")

    def _detect_encryption(self, m3u8_content, playlist=None):
        """
        检测m3u8文件是否加密

        Args:
            m3u8_content: m3u8文件内容（字符串）
            playlist: m3u8库解析的playlist对象（可选）

        Returns:
            dict: 加密信息字典
        """
        encryption_info = {
            "is_encrypted": False,
            "method": None,
            "key_uri": None,
            "key_file": "encryption.key",
            "iv": None,
            "keyformat": None,
            "keyformatversions": None,
        }

        # 方法1: 使用m3u8库的keys属性
        if playlist and hasattr(playlist, "keys") and playlist.keys:
            for key in playlist.keys:
                if key and key.method and key.method.upper() != "NONE":
                    encryption_info["is_encrypted"] = True
                    encryption_info["method"] = key.method
                    encryption_info["key_uri"] = key.uri
                    encryption_info["iv"] = key.iv
                    encryption_info["keyformat"] = key.keyformat
                    encryption_info["keyformatversions"] = key.keyformatversions
                    break  # 只取第一个加密密钥

        # 方法2: 手动解析（备用方案）
        if not encryption_info["is_encrypted"]:
            # 查找 #EXT-X-KEY 标签
            key_pattern = r'#EXT-X-KEY:(.+)'
            key_matches = re.findall(key_pattern, m3u8_content)

            for key_line in key_matches:
                # 解析KEY属性
                method_match = re.search(r'METHOD=([^,\s]+)', key_line)
                if method_match:
                    method = method_match.group(1).strip('"')
                    if method.upper() != "NONE":
                        encryption_info["is_encrypted"] = True
                        encryption_info["method"] = method

                        # 提取URI
                        uri_match = re.search(r'URI="([^"]+)"', key_line)
                        if uri_match:
                            encryption_info["key_uri"] = uri_match.group(1)

                        # 提取IV
                        iv_match = re.search(r'IV=(0x[0-9A-Fa-f]+)', key_line)
                        if iv_match:
                            encryption_info["iv"] = iv_match.group(1)

                        # 提取KEYFORMAT
                        keyformat_match = re.search(r'KEYFORMAT="([^"]+)"', key_line)
                        if keyformat_match:
                            encryption_info["keyformat"] = keyformat_match.group(1)

                        # 提取KEYFORMATVERSIONS
                        keyformatversions_match = re.search(
                            r'KEYFORMATVERSIONS="([^"]+)"', key_line
                        )
                        if keyformatversions_match:
                            encryption_info["keyformatversions"] = (
                                keyformatversions_match.group(1)
                            )

                        break  # 只取第一个加密密钥

        return encryption_info

    def _parse_m3u8_manual(self, m3u8_content):
        """手动解析m3u8文件（备用方法）"""
        # 检测加密（手动解析模式）
        encryption_info = self._detect_encryption(m3u8_content, None)

        # 保存加密信息
        encryption_info_path = os.path.join(
            self.download_directory, "encryption_info.json"
        )
        with open(encryption_info_path, "w", encoding="utf-8") as f:
            json.dump(encryption_info, f, indent=2, ensure_ascii=False)

        # 输出加密状态
        if encryption_info["is_encrypted"]:
            self.logger.info(
                f"⚠️  检测到加密: {encryption_info['method']}, "
                f"密钥URI: {encryption_info['key_uri']}"
            )

            # 下载密钥文件
            if encryption_info["key_uri"]:
                key_url = encryption_info["key_uri"]
                # 处理相对URL
                if not key_url.startswith("http"):
                    if key_url.startswith("/"):
                        key_url = urljoin(self.base_url, key_url)
                    else:
                        base_dir = os.path.dirname(urlparse(self.m3u8_url).path)
                        if base_dir:
                            key_url = urljoin(f"{self.base_url}{base_dir}/", key_url)
                        else:
                            key_url = urljoin(f"{self.base_url}/", key_url)

                self.logger.info(f"正在下载密钥文件: {key_url}")
                # 下载密钥文件
                yield Request(
                    url=key_url,
                    callback=self._save_encryption_key,
                    dont_filter=True,
                )
        else:
            self.logger.info("✅ 未检测到加密，m3u8文件为非加密格式")

        lines = m3u8_content.strip().split("\n")
        segment_index = 0

        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 如果是URL
            if line.startswith("http") or not line.startswith("#"):
                segment_url = line
                if not segment_url.startswith("http"):
                    # 相对URL
                    if segment_url.startswith("/"):
                        segment_url = urljoin(self.base_url, segment_url)
                    else:
                        base_dir = os.path.dirname(urlparse(self.m3u8_url).path)
                        if base_dir:
                            segment_url = urljoin(
                                f"{self.base_url}{base_dir}/", segment_url
                            )
                        else:
                            segment_url = urljoin(f"{self.base_url}/", segment_url)

                # 生成文件名
                segment_filename = os.path.basename(segment_url)
                if not segment_filename or not segment_filename.endswith(".ts"):
                    segment_filename = f"segment_{segment_index:05d}.ts"

                # 创建item
                item = M3U8Item()
                item["url"] = segment_url
                item["filename"] = segment_filename
                item["directory"] = self.download_directory
                item["segment_index"] = segment_index

                yield item
                segment_index += 1
