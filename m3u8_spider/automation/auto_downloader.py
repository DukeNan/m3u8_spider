#!/usr/bin/env python3
"""
自动下载协调器
从数据库读取任务，调用下载和校验模块，更新任务状态
"""

from __future__ import annotations

import signal
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

from m3u8_spider.config import (
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    DOWNLOAD_COOLDOWN_SECONDS,
    INVALID_FILENAME_CHARS,
    MYSQL_CONNECT_TIMEOUT,
    MYSQL_READ_TIMEOUT,
    MYSQL_WRITE_TIMEOUT,
)
from m3u8_spider.database.manager import DatabaseManager, DownloadTask, TaskStatus
from m3u8_spider.logger import get_logger
from m3u8_spider.core.recovery import recover_download
from m3u8_spider.core.downloader import DownloadConfig
from tqdm import tqdm

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class AutoDownloadConfig:
    """自动下载器配置"""

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_database: str
    check_interval: int = 60
    concurrent: int = DEFAULT_CONCURRENT
    delay: float = DEFAULT_DELAY
    batch_size: int = 1  # 每次处理的任务数
    cooldown_seconds: int = DOWNLOAD_COOLDOWN_SECONDS  # 下载完成后的冷却时间（秒）


@dataclass
class DownloadStats:
    """下载统计信息"""

    total_processed: int = 0
    success_count: int = 0
    failed_count: int = 0

    def record_success(self) -> None:
        """记录成功"""
        self.total_processed += 1
        self.success_count += 1

    def record_failure(self) -> None:
        """记录失败"""
        self.total_processed += 1
        self.failed_count += 1

    def print_summary(self) -> None:
        """打印统计摘要"""
        sep = "=" * 60
        logger.info(f"\n{sep}")
        logger.info("📊 下载统计")
        logger.info(sep)
        logger.info(f"总处理数: {self.total_processed}")
        logger.info(f"成功: {self.success_count}")
        logger.info(f"失败: {self.failed_count}")
        if self.total_processed > 0:
            success_rate = (self.success_count / self.total_processed) * 100
            logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"{sep}\n")


# ---------------------------------------------------------------------------
# 自动下载器
# ---------------------------------------------------------------------------


class AutoDownloader:
    """
    自动下载协调器
    负责从数据库读取任务、调用下载、校验、更新状态
    """

    def __init__(self, config: AutoDownloadConfig) -> None:
        self._config = config
        self._db_manager = DatabaseManager(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_database,
            connect_timeout=MYSQL_CONNECT_TIMEOUT,
            read_timeout=MYSQL_READ_TIMEOUT,
            write_timeout=MYSQL_WRITE_TIMEOUT,
        )
        self._stats = DownloadStats()
        self._running = True
        self._project_root = Path(__file__).resolve().parent.parent.parent

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        """处理中断信号（Ctrl+C）"""
        # 第一次收到信号：设置标志，准备优雅退出
        if self._running:
            logger.warning("\n\n⚠️  收到中断信号，正在优雅退出...")
            self._running = False
        else:
            # 第二次收到信号：强制退出
            logger.error("\n\n⚠️  再次收到中断信号，强制退出...")
            sys.exit(1)

    def run(self) -> None:
        """主循环：守护进程模式"""
        logger.info("🚀 自动下载器启动")
        self._print_config()

        if not self._db_manager.connect():
            logger.error("❌ 无法连接数据库，退出")
            sys.exit(1)

        try:
            self._main_loop()
        except Exception as e:
            logger.exception(f"❌ 发生未预期的错误: {e}")
            traceback.print_exc()
        finally:
            self._cleanup()

    def _print_config(self) -> None:
        """打印配置信息"""
        sep = "=" * 60
        logger.info(f"\n{sep}")
        logger.info("配置信息")
        logger.info(sep)
        logger.info(
            f"数据库: {self._config.db_host}:{self._config.db_port}/{self._config.db_database}"
        )
        logger.info(f"检查间隔: {self._config.check_interval} 秒")
        logger.info(f"并发数: {self._config.concurrent}")
        logger.info(f"下载延迟: {self._config.delay} 秒")
        logger.info(f"批次大小: {self._config.batch_size}")
        logger.info(f"冷却时间: {self._config.cooldown_seconds} 秒")
        logger.info(f"{sep}\n")

    def _main_loop(self) -> None:
        """主循环：持续检查并处理任务"""
        while self._running:
            # 获取数据库统计
            db_stats = self._db_manager.get_statistics()
            logger.info(
                f"\n📊 数据库状态: 总计={db_stats['total']}, "
                f"待下载={db_stats['pending']}, "
                f"成功={db_stats['success']}, "
                f"失败={db_stats['failed']}"
            )

            # 检查是否有待下载任务
            if db_stats["pending"] == 0:
                logger.info(
                    f"✅ 没有待下载任务，{self._config.check_interval} 秒后再次检查..."
                )
                self._sleep_with_interrupt(self._config.check_interval)
                continue

            # 获取待下载任务
            tasks = self._db_manager.get_pending_tasks(limit=self._config.batch_size)
            if not tasks:
                logger.warning(
                    f"⚠️  未能获取任务，{self._config.check_interval} 秒后重试..."
                )
                self._sleep_with_interrupt(self._config.check_interval)
                continue

            # 处理每个任务
            has_cooldown = False
            for task in tasks:
                if not self._running:
                    logger.warning("⚠️  收到停止信号，中断任务处理")
                    break

                self._process_task(task)

                # 任务完成后倒计时（仅在有更多任务或将要循环检查时）
                if self._running and self._config.cooldown_seconds > 0:
                    self._countdown_with_progress(
                        self._config.cooldown_seconds, "任务完成，冷却倒计时"
                    )
                    has_cooldown = True

            # 如果已经执行了冷却倒计时，则直接进入下一轮检查，不再额外等待
            # 只有在没有冷却时间时，才使用 check_interval 作为任务之间的间隔
            if self._running and not has_cooldown:
                logger.info(f"\n⏳ 等待 {self._config.check_interval} 秒后继续...")
                self._sleep_with_interrupt(self._config.check_interval)

    def _sleep_with_interrupt(self, seconds: int) -> None:
        """可中断的睡眠"""
        try:
            for _ in range(seconds):
                if not self._running:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            # 如果用户在等待期间按 CTRL+C，立即退出
            self._running = False
            raise

    def _countdown_with_progress(
        self, seconds: int, description: str = "等待中"
    ) -> None:
        """
        带进度条的倒计时（使用 tqdm）

        Args:
            seconds: 倒计时秒数
            description: 描述文字
        """
        logger.info(f"\n⏱️  {description}: {seconds} 秒")

        # 使用 tqdm 创建进度条
        try:
            with tqdm(
                total=seconds,
                desc=f"⏱️  {description}",
                unit="秒",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}秒 [{elapsed}<{remaining}]",
            ) as pbar:
                for _ in range(seconds):
                    if not self._running:
                        tqdm.write("⚠️  倒计时被中断")
                        break
                    time.sleep(1)
                    pbar.update(1)
        except KeyboardInterrupt:
            # 如果用户在倒计时期间按 CTRL+C，立即退出
            tqdm.write("⚠️  倒计时被中断")
            self._running = False
            raise

        if self._running:
            logger.info("✅ 等待完成，继续下一个任务\n")

    def _process_task(self, task: DownloadTask) -> None:
        """处理单个下载任务"""
        sep = "=" * 60
        logger.info(f"\n{sep}")
        logger.info("📥 开始处理任务")
        logger.info(sep)
        logger.info(f"ID: {task.id}")
        logger.info(f"编号: {task.number}")
        logger.info(f"标题: {task.title or 'N/A'}")
        logger.info(f"提供商: {task.provider or 'N/A'}")
        logger.info(f"M3U8: {task.m3u8_address}")
        logger.info(f"{sep}\n")

        try:
            # 1. 创建下载配置
            filename = self._sanitize_filename(task.number)
            download_config = DownloadConfig(
                m3u8_url=task.m3u8_address,
                filename=filename,
                concurrent=self._config.concurrent,
                delay=self._config.delay,
            )

            # 2. 执行恢复流程（补元数据 -> 校验 -> 仅重下失败TS）
            logger.info(f"⬇️  开始下载恢复流程: {filename}")
            recovery_result = recover_download(download_config, max_retry_rounds=3)
            is_complete = recovery_result.is_complete
            result = recovery_result.validation_result

            # 3. 更新数据库状态
            if is_complete:
                logger.info(f"✅ 校验通过: {filename}")
                if recovery_result.retry_rounds > 0:
                    logger.info(f"   重试轮次: {recovery_result.retry_rounds}")
                logger.info(
                    f"💾 正在写入数据库 (task_id={task.id}, status=1)..."
                )
                self._db_manager.update_task_status(
                    task.id, status=TaskStatus.SUCCESS, update_m3u8_time=True
                )
                self._stats.record_success()
                logger.info("✅ 已更新数据库状态: status=1 (成功)")
            else:
                logger.error(f"❌ 校验失败: {filename}")
                failed_count = len(result.get("failed_files", []))
                logger.error(f"   失败文件数: {failed_count}")
                logger.error("   已达到最大重试轮次: 3")
                logger.info(
                    f"💾 正在写入数据库 (task_id={task.id}, status=2)..."
                )
                self._db_manager.update_task_status(
                    task.id, status=TaskStatus.FAILED, update_m3u8_time=True
                )
                self._stats.record_failure()
                logger.warning("⚠️  已更新数据库状态: status=2 (失败)")

        except Exception as e:
            logger.exception(f"❌ 处理任务失败 (ID={task.id}): {e}")
            traceback.print_exc()

            # 更新为失败状态
            self._db_manager.update_task_status(task.id, status=TaskStatus.FAILED)
            self._stats.record_failure()
            logger.warning("⚠️  已更新数据库状态: status=2 (异常失败)")

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名（移除不合法字符）"""
        name = filename.strip()
        for char in INVALID_FILENAME_CHARS:
            name = name.replace(char, "_")
        return name

    def _cleanup(self) -> None:
        """清理资源"""
        logger.info("\n🧹 正在清理资源...")
        self._db_manager.close()
        self._stats.print_summary()
        logger.info("👋 自动下载器已退出")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def create_auto_downloader(
    db_host: str,
    db_port: int,
    db_user: str,
    db_password: str,
    db_database: str,
    check_interval: int = 60,
    concurrent: int = DEFAULT_CONCURRENT,
    delay: float = DEFAULT_DELAY,
    cooldown_seconds: int = DOWNLOAD_COOLDOWN_SECONDS,
) -> AutoDownloader:
    """
    创建自动下载器实例

    Args:
        db_host: 数据库主机
        db_port: 数据库端口
        db_user: 数据库用户
        db_password: 数据库密码
        db_database: 数据库名称
        check_interval: 检查间隔（秒）
        concurrent: 并发数
        delay: 下载延迟（秒）
        cooldown_seconds: 下载完成后的冷却时间（秒）

    Returns:
        AutoDownloader 实例
    """
    config = AutoDownloadConfig(
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
        db_password=db_password,
        db_database=db_database,
        check_interval=check_interval,
        concurrent=concurrent,
        delay=delay,
        cooldown_seconds=cooldown_seconds,
    )
    return AutoDownloader(config)