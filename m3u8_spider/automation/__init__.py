"""自动化守护进程模块"""

from m3u8_spider.automation.auto_downloader import (
    AutoDownloader,
    AutoDownloadConfig,
    create_auto_downloader,
)

__all__ = ["AutoDownloader", "AutoDownloadConfig", "create_auto_downloader"]