# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import json
from urllib.parse import urlparse
from scrapy import Request
from scrapy.pipelines.files import FilesPipeline


class M3U8FilePipeline(FilesPipeline):
    """M3U8文件下载管道"""

    def __init__(self, store_uri, download_func=None, settings=None, crawler=None):
        # 兼容新旧版本的FilesPipeline
        if crawler is not None:
            super().__init__(store_uri, crawler=crawler)
        else:
            super().__init__(store_uri, download_func, settings)
        self.download_directory = None
        self.content_lengths = {}  # 存储文件名到Content-Length的映射

    @classmethod
    def from_crawler(cls, crawler):
        """从crawler创建pipeline实例"""
        store_uri = crawler.settings.get('FILES_STORE', 'downloads')
        return cls(store_uri=store_uri, crawler=crawler)

    @classmethod
    def from_settings(cls, settings):
        """从settings创建pipeline实例（兼容旧版本）"""
        store_uri = settings.get('FILES_STORE', 'downloads')
        return cls(store_uri=store_uri, settings=settings)

    def open_spider(self, spider):
        """爬虫启动时调用"""
        super().open_spider(spider)
        # 从spider获取下载目录
        if hasattr(spider, 'download_directory'):
            self.download_directory = spider.download_directory
            # 确保目录存在
            os.makedirs(self.download_directory, exist_ok=True)
            # 设置store的basedir为下载目录
            self.store.basedir = self.download_directory

            # 加载已有的Content-Length信息（如果存在）
            content_lengths_file = os.path.join(self.download_directory, "content_lengths.json")
            if os.path.exists(content_lengths_file):
                try:
                    with open(content_lengths_file, 'r', encoding='utf-8') as f:
                        self.content_lengths = json.load(f)
                except Exception:
                    self.content_lengths = {}

    def close_spider(self, spider):
        """爬虫关闭时调用，保存Content-Length信息"""
        if self.download_directory and self.content_lengths:
            content_lengths_file = os.path.join(self.download_directory, "content_lengths.json")
            try:
                with open(content_lengths_file, 'w', encoding='utf-8') as f:
                    json.dump(self.content_lengths, f, indent=2, ensure_ascii=False)
            except Exception as e:
                if hasattr(spider, 'logger'):
                    spider.logger.warning(f"无法保存Content-Length信息: {e}")

    def file_path(self, request, response=None, info=None, *, item=None):
        """返回文件保存路径（相对路径）"""
        # 从request meta获取item信息
        if hasattr(request, 'meta') and 'item' in request.meta:
            item = request.meta['item']

        if item and 'filename' in item:
            filename = item['filename']
        else:
            # 从URL提取文件名
            url_path = urlparse(request.url).path
            filename = os.path.basename(url_path) or f"segment_{item.get('segment_index', 0) if item else 0}.ts"

        return filename

    def get_media_requests(self, item, info):
        """生成下载请求"""
        yield Request(item['url'], meta={'item': item})

    def item_completed(self, results, item, info):
        """文件下载完成后的处理"""
        if results:
            ok, result = results[0]
            if ok:
                # 文件路径是相对路径
                file_path = result['path']
                # 构建完整路径
                if self.download_directory:
                    full_path = os.path.join(self.download_directory, file_path)
                else:
                    full_path = file_path

                # 从result中获取Content-Length（如果可用）
                # result包含 {'url', 'path', 'checksum', 'status'}
                # 注意：FilesPipeline不直接提供response对象，我们需要从其他地方获取
                # 我们可以在media_downloaded中获取

                # 安全地设置字段（检查字段是否在item定义中）
                if 'file_path' in item.fields:
                    item['file_path'] = full_path
                if 'file_status' in item.fields:
                    item['file_status'] = 'downloaded'
            else:
                if 'file_status' in item.fields:
                    item['file_status'] = 'failed'
                if 'file_error' in item.fields:
                    item['file_error'] = result
        return item

    def media_downloaded(self, response, request, info, *, item=None):
        """下载完成后调用，可以获取response headers"""
        # 获取Content-Length
        content_length = response.headers.get(b'Content-Length')
        if content_length and item:
            try:
                length = int(content_length.decode('utf-8'))
                filename = item.get('filename', '')
                if filename:
                    self.content_lengths[filename] = length
            except Exception:
                pass

        # 调用父类方法继续处理
        return super().media_downloaded(response, request, info, item=item)