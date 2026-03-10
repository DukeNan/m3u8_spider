#!/usr/bin/env python3
"""
M3U8 URL 刷新守护进程
从数据库读取带页面 URL 的任务，爬取页面解析 M3U8 地址并写回数据库
"""

from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass

from m3u8_spider.config import (
    M3U8_REFRESH_INTERVAL,
    M3U8_REFRESH_MIN_MINUTES,
)
from m3u8_spider.database.manager import DatabaseManager, DownloadTask
from m3u8_spider.logger import get_logger
from m3u8_spider.core.m3u8_fetcher import fetch_m3u8_from_page

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 配置与统计
# ---------------------------------------------------------------------------


@dataclass
class M3U8RefresherConfig:
    """M3U8 刷新守护进程配置"""

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_database: str
    check_interval: int = M3U8_REFRESH_INTERVAL
    min_minutes_since_update: int = M3U8_REFRESH_MIN_MINUTES
    batch_size: int = 30


@dataclass
class RefreshStats:
    """刷新统计"""

    total_processed: int = 0
    success_count: int = 0
    skip_count: int = 0  # 未解析到 M3U8 跳过
    error_count: int = 0

    def record_success(self) -> None:
        self.total_processed += 1
        self.success_count += 1

    def record_skip(self) -> None:
        self.total_processed += 1
        self.skip_count += 1

    def record_error(self) -> None:
        self.total_processed += 1
        self.error_count += 1

    def print_summary(self) -> None:
        sep = "=" * 60
        logger.info(f"\n{sep}")
        logger.info("📊 M3U8 刷新统计")
        logger.info(sep)
        logger.info(f"总处理数: {self.total_processed}")
        logger.info(f"成功更新: {self.success_count}")
        logger.info(f"未解析到: {self.skip_count}")
        logger.info(f"异常: {self.error_count}")
        logger.info(f"{sep}\n")


# ---------------------------------------------------------------------------
# M3U8 刷新器
# ---------------------------------------------------------------------------


class M3U8Refresher:
    """
    M3U8 URL 刷新守护进程
    查询 status != 1 且具备 url 的任务，爬取页面得到 M3U8 地址并更新数据库
    """

    def __init__(self, config: M3U8RefresherConfig) -> None:
        self._config = config
        self._db_manager = DatabaseManager(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_database,
        )
        self._stats = RefreshStats()
        self._running = True

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        if self._running:
            logger.warning("\n\n⚠️  收到中断信号，正在优雅退出...")
            self._running = False
        else:
            logger.error("\n\n⚠️  再次收到中断信号，强制退出...")
            sys.exit(1)

    def run(self) -> None:
        """主循环"""
        logger.info("🔄 M3U8 URL 刷新守护进程启动")
        self._print_config()

        if not self._db_manager.connect():
            logger.error("❌ 无法连接数据库，退出")
            sys.exit(1)

        try:
            self._main_loop()
        except Exception as e:
            logger.error(f"❌ 发生未预期的错误: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self._cleanup()

    def _print_config(self) -> None:
        sep = "=" * 60
        logger.info(f"\n{sep}")
        logger.info("配置信息")
        logger.info(sep)
        logger.info(
            f"数据库: {self._config.db_host}:{self._config.db_port}/{self._config.db_database}"
        )
        logger.info(f"检查间隔: {self._config.check_interval} 秒")
        logger.info(f"最小更新间隔: {self._config.min_minutes_since_update} 分钟")
        logger.info(f"批次大小: {self._config.batch_size}")
        logger.info(f"{sep}\n")

    def _main_loop(self) -> None:
        while self._running:
            tasks = self._db_manager.get_tasks_for_m3u8_refresh(
                limit=self._config.batch_size,
                min_minutes_since_update=self._config.min_minutes_since_update,
            )

            if not tasks:
                logger.info(
                    f"✅ 暂无待刷新任务，{self._config.check_interval} 秒后再次检查..."
                )
                self._sleep_with_interrupt(self._config.check_interval)
                continue

            logger.info(f"📋 本轮待刷新任务数: {len(tasks)}")
            for task in tasks:
                if not self._running:
                    break
                self._process_task(task)

            if self._running:
                logger.info(
                    f"⏳ 等待 {self._config.check_interval} 秒后继续..."
                )
                self._sleep_with_interrupt(self._config.check_interval)

    def _sleep_with_interrupt(self, seconds: int) -> None:
        try:
            for _ in range(seconds):
                if not self._running:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            self._running = False
            raise

    def _process_task(self, task: DownloadTask) -> None:
        page_url = task.url
        if not page_url or not page_url.strip():
            logger.warning(f"⚠️  任务 {task.number} (id={task.id}) 无 url，跳过")
            self._stats.record_skip()
            return

        logger.info(f"🔄 [{task.number}] 抓取页面: {page_url[:80]}...")
        try:
            m3u8_url = fetch_m3u8_from_page(page_url)
            if m3u8_url:
                if self._db_manager.update_m3u8_address(task.id, m3u8_url):
                    logger.info(f"✅ [{task.number}] 已更新 M3U8 地址")
                    self._stats.record_success()
                else:
                    logger.warning(f"⚠️  [{task.number}] 更新数据库失败")
                    self._stats.record_error()
            else:
                logger.warning(f"⚠️  [{task.number}] 未解析到 M3U8 URL，跳过")
                self._stats.record_skip()
        except ImportError as e:
            logger.error(f"❌ 依赖未安装: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [{task.number}] 处理失败: {e}")
            self._stats.record_error()

    def _cleanup(self) -> None:
        logger.info("\n🧹 正在清理资源...")
        self._db_manager.close()
        self._stats.print_summary()
        logger.info("👋 M3U8 刷新守护进程已退出")


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------


def create_m3u8_refresher(
    db_host: str,
    db_port: int,
    db_user: str,
    db_password: str,
    db_database: str,
    check_interval: int = M3U8_REFRESH_INTERVAL,
    min_minutes_since_update: int = M3U8_REFRESH_MIN_MINUTES,
    batch_size: int = 30,
) -> M3U8Refresher:
    """创建 M3U8 刷新器实例"""
    config = M3U8RefresherConfig(
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
        db_password=db_password,
        db_database=db_database,
        check_interval=check_interval,
        min_minutes_since_update=min_minutes_since_update,
        batch_size=batch_size,
    )
    return M3U8Refresher(config)
