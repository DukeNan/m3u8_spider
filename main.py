#!/usr/bin/env python3
"""
M3U8下载工具主入口
使用Scrapy框架下载M3U8文件中的视频片段
"""

import sys
import os
import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 添加scrapy项目路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scrapy_project'))

from m3u8_spider.spiders.m3u8_downloader import M3U8DownloaderSpider


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='M3U8文件下载工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py https://example.com/playlist.m3u8 my_video
  python main.py https://example.com/playlist.m3u8 video_name --concurrent 16
        """
    )

    parser.add_argument(
        'm3u8_url',
        help='M3U8文件的URL地址'
    )

    parser.add_argument(
        'filename',
        help='保存的文件名（将创建同名目录）'
    )

    parser.add_argument(
        '--concurrent',
        type=int,
        default=32,
        help='并发下载数（默认: 32）'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0,
        help='下载延迟（秒，默认: 0）'
    )

    args = parser.parse_args()

    # 验证参数
    if not args.m3u8_url.startswith(('http://', 'https://')):
        print(f"错误: 无效的URL: {args.m3u8_url}")
        sys.exit(1)

    if not args.filename or not args.filename.strip():
        print("错误: 文件名不能为空")
        sys.exit(1)

    # 清理文件名（移除不合法字符）
    filename = args.filename.strip()
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    print(f"\n{'='*60}")
    print(f"M3U8下载工具")
    print(f"{'='*60}")
    print(f"M3U8 URL: {args.m3u8_url}")
    print(f"保存目录: {filename}")
    print(f"并发数: {args.concurrent}")
    print(f"下载延迟: {args.delay}秒")
    print(f"{'='*60}\n")

    # 设置Scrapy项目路径
    project_dir = os.path.join(os.path.dirname(__file__), 'scrapy_project')
    os.chdir(project_dir)

    # 获取Scrapy设置
    settings = get_project_settings()

    # 更新设置
    settings.set('CONCURRENT_REQUESTS', args.concurrent)
    settings.set('DOWNLOAD_DELAY', args.delay)

    # 创建爬虫进程
    process = CrawlerProcess(settings)

    # 启动爬虫
    process.crawl(
        M3U8DownloaderSpider,
        m3u8_url=args.m3u8_url,
        filename=filename
    )

    # 开始爬取
    print("开始下载...\n")
    process.start()

    # 恢复工作目录
    os.chdir(os.path.dirname(__file__))

    print(f"\n{'='*60}")
    print("下载完成!")
    print(f"文件保存在: {os.path.join(os.path.dirname(__file__), filename)}")
    print(f"{'='*60}\n")

    print("下一步操作:")
    print(f"  1. 校验文件: python validate_downloads.py {filename}")
    print(f"  2. 合并为MP4: python merge_to_mp4.py {filename}")


if __name__ == "__main__":
    main()
