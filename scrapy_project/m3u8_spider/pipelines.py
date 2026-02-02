# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
from pathlib import Path
from urllib.parse import urlparse
from scrapy import Request
from scrapy.pipelines.files import FilesPipeline
from scrapy.utils.project import get_project_settings


class M3U8FilePipeline(FilesPipeline):
    """M3U8文件下载管道"""

    def __init__(self, store_uri, download_func=None, settings=None):
        super().__init__(store_uri, download_func, settings)
        self.download_directory = None

    @classmethod
    def from_settings(cls, settings):
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
                    item['file_path'] = full_path
                else:
                    item['file_path'] = file_path
                item['file_status'] = 'downloaded'
            else:
                item['file_status'] = 'failed'
                item['file_error'] = result
        return item
