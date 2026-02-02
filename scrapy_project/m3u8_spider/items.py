# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class M3U8Item(scrapy.Item):
    """M3U8下载项"""
    url = scrapy.Field()  # ts文件URL
    filename = scrapy.Field()  # 保存的文件名
    directory = scrapy.Field()  # 保存目录
    segment_index = scrapy.Field()  # 片段索引
