#!/usr/bin/env python3
"""
M3U8下载工具主入口
使用Scrapy框架下载M3U8文件中的视频片段
"""

import sys
import os
import re
import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 添加scrapy项目路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scrapy_project'))

from m3u8_spider.spiders.m3u8_downloader import M3U8DownloaderSpider

# 导入校验和合并函数
from validate_downloads import validate_downloads
from merge_to_mp4 import merge_ts_files


def download_m3u8(m3u8_url, filename, concurrent, delay, retry_urls=None):
    """
    下载M3U8文件

    Args:
        m3u8_url: M3U8文件URL
        filename: 保存的文件名
        concurrent: 并发数
        delay: 下载延迟
        retry_urls: 重试URL列表（可选）
    """
    # 设置Scrapy项目路径
    project_dir = os.path.join(os.path.dirname(__file__), 'scrapy_project')
    original_dir = os.getcwd()
    os.chdir(project_dir)

    try:
        # 获取Scrapy设置
        settings = get_project_settings()

        # 更新设置
        settings.set('CONCURRENT_REQUESTS', concurrent)
        settings.set('DOWNLOAD_DELAY', delay)

        # 创建爬虫进程
        process = CrawlerProcess(settings)

        # 启动爬虫
        process.crawl(
            M3U8DownloaderSpider,
            m3u8_url=m3u8_url,
            filename=filename,
            retry_urls=retry_urls
        )

        # 开始爬取
        process.start()
    finally:
        # 恢复工作目录
        os.chdir(original_dir)


def retry_failed_downloads(directory, failed_urls, m3u8_url, filename, concurrent, delay, max_retries=3):
    """
    重试失败的下载

    Args:
        directory: 下载目录
        failed_urls: 失败文件的URL映射 {filename: url}
        m3u8_url: M3U8文件URL
        filename: 保存的文件名
        concurrent: 并发数
        delay: 下载延迟
        max_retries: 最大重试次数

    Returns:
        bool: 是否全部成功
    """
    retry_count = 0
    remaining_failures = failed_urls.copy()

    while retry_count < max_retries and remaining_failures:
        retry_count += 1
        print(f"\n{'='*60}")
        print(f"第 {retry_count} 次重试")
        print(f"{'='*60}")
        print(f"需要重试的文件数量: {len(remaining_failures)}")

        # 删除失败的文件
        for fname in remaining_failures.keys():
            filepath = os.path.join(directory, fname)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"已删除损坏文件: {fname}")
                except Exception as e:
                    print(f"无法删除文件 {fname}: {e}")

        # 构建重试URL列表
        retry_urls = []
        for fname, url in remaining_failures.items():
            # 从文件名提取索引
            match = re.match(r'segment_(\d+)\.ts', fname)
            index = int(match.group(1)) if match else 0

            retry_urls.append({
                'url': url,
                'filename': fname,
                'index': index
            })

        # 重新下载
        print(f"\n开始重试下载 {len(retry_urls)} 个文件...\n")
        download_m3u8(m3u8_url, filename, concurrent, delay, retry_urls=retry_urls)

        # 重新校验
        print(f"\n重新校验下载结果...")
        is_complete, result = validate_downloads(directory)

        if is_complete:
            print(f"✅ 重试成功！所有文件已完整下载")
            return True

        # 更新剩余失败的文件
        remaining_failures = result.get('failed_urls', {})

        if remaining_failures:
            print(f"\n仍有 {len(remaining_failures)} 个文件失败")
            if retry_count < max_retries:
                print(f"将进行第 {retry_count + 1} 次重试...")

    # 最终仍有失败
    if remaining_failures:
        print(f"\n❌ 重试 {max_retries} 次后，仍有 {len(remaining_failures)} 个文件失败")
        return False

    return True


def save_failed_files_log(directory, failed_urls):
    """
    保存失败文件日志

    Args:
        directory: 下载目录
        failed_urls: 失败文件的URL映射
    """
    if not failed_urls:
        return

    log_file = os.path.join(directory, "failed_files.txt")
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"失败文件列表 (共 {len(failed_urls)} 个)\n")
            f.write("="*60 + "\n\n")
            for filename, url in sorted(failed_urls.items()):
                f.write(f"文件名: {filename}\n")
                f.write(f"URL: {url}\n")
                f.write("-"*60 + "\n")
        print(f"\n失败文件列表已保存到: {log_file}")
    except Exception as e:
        print(f"\n无法保存失败文件日志: {e}")


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

    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='下载完成后不自动合并为MP4'
    )

    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='失败文件的最大重试次数（默认: 3）'
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
    print(f"最大重试次数: {args.max_retries}")
    print(f"自动合并: {'否' if args.no_merge else '是'}")
    print(f"{'='*60}\n")

    # 获取下载目录路径
    download_dir = os.path.join(os.path.dirname(__file__), filename)

    # 步骤1: 下载
    print("开始下载...\n")
    download_m3u8(args.m3u8_url, filename, args.concurrent, args.delay)

    print(f"\n{'='*60}")
    print("初始下载完成!")
    print(f"{'='*60}\n")

    # 步骤2: 校验
    print("开始校验下载结果...")
    is_complete, validation_result = validate_downloads(download_dir)

    # 步骤3: 重试（如果需要）
    if not is_complete:
        failed_urls = validation_result.get('failed_urls', {})
        if failed_urls:
            print(f"\n发现 {len(failed_urls)} 个失败文件，开始重试...")
            retry_success = retry_failed_downloads(
                download_dir,
                failed_urls,
                args.m3u8_url,
                filename,
                args.concurrent,
                args.delay,
                args.max_retries
            )

            if retry_success:
                is_complete = True
            else:
                # 保存失败文件日志
                _, final_result = validate_downloads(download_dir)
                final_failed = final_result.get('failed_urls', {})
                if final_failed:
                    save_failed_files_log(download_dir, final_failed)

    # 步骤4: 合并（如果完成且未禁用）
    if is_complete and not args.no_merge:
        print(f"\n{'='*60}")
        print("开始合并为MP4...")
        print(f"{'='*60}\n")

        merge_success = merge_ts_files(download_dir)

        if merge_success:
            print(f"\n{'='*60}")
            print("✅ 全部完成!")
            print(f"文件保存在: {download_dir}")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print("⚠️  合并失败，但文件已下载完成")
            print(f"文件保存在: {download_dir}")
            print(f"{'='*60}\n")
            print("可以手动合并:")
            print(f"  python merge_to_mp4.py {filename}")
    elif is_complete:
        print(f"\n{'='*60}")
        print("✅ 下载完成!")
        print(f"文件保存在: {download_dir}")
        print(f"{'='*60}\n")
        print("下一步操作:")
        print(f"  合并为MP4: python merge_to_mp4.py {filename}")
    else:
        print(f"\n{'='*60}")
        print("❌ 下载未完成")
        print(f"文件保存在: {download_dir}")
        print(f"{'='*60}\n")
        print("部分文件下载失败，请查看 failed_files.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
