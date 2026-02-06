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
    file_path = scrapy.Field()  # 文件保存的完整路径（由pipeline设置）
    file_status = (
        scrapy.Field()
    )  # 文件下载状态：'downloaded' 或 'failed'（由pipeline设置）
    file_error = scrapy.Field()  # 文件下载错误信息（由pipeline设置，如果下载失败）
