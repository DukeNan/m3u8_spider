import os
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
            self._parse_m3u8_manual(response.text)

    def _parse_m3u8_manual(self, m3u8_content):
        """手动解析m3u8文件（备用方法）"""
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
