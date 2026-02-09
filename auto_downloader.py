#!/usr/bin/env python3
"""
自动下载协调器
从数据库读取任务，调用下载和校验模块，更新任务状态
"""

from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from db_manager import DatabaseManager, DownloadTask
from main import (
    DownloadConfig,
    _run_scrapy,
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    INVALID_FILENAME_CHARS,
)
from validate_downloads import validate_downloads


# ---------------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------------

# 下载完成后的等待时间（秒）
DOWNLOAD_COOLDOWN_SECONDS = 30


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
        print(f"\n{sep}")
        print("📊 下载统计")
        print(sep)
        print(f"总处理数: {self.total_processed}")
        print(f"成功: {self.success_count}")
        print(f"失败: {self.failed_count}")
        if self.total_processed > 0:
            success_rate = (self.success_count / self.total_processed) * 100
            print(f"成功率: {success_rate:.1f}%")
        print(f"{sep}\n")


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
        )
        self._stats = DownloadStats()
        self._running = True
        self._project_root = Path(__file__).resolve().parent

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        """处理中断信号（Ctrl+C）"""
        print("\n\n⚠️  收到中断信号，正在优雅退出...")
        self._running = False

    def run(self) -> None:
        """主循环：守护进程模式"""
        print("🚀 自动下载器启动")
        self._print_config()

        if not self._db_manager.connect():
            print("❌ 无法连接数据库，退出")
            sys.exit(1)

        try:
            self._main_loop()
        except Exception as e:
            print(f"❌ 发生未预期的错误: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self._cleanup()

    def _print_config(self) -> None:
        """打印配置信息"""
        sep = "=" * 60
        print(f"\n{sep}")
        print("配置信息")
        print(sep)
        print(
            f"数据库: {self._config.db_host}:{self._config.db_port}/{self._config.db_database}"
        )
        print(f"检查间隔: {self._config.check_interval} 秒")
        print(f"并发数: {self._config.concurrent}")
        print(f"下载延迟: {self._config.delay} 秒")
        print(f"批次大小: {self._config.batch_size}")
        print(f"冷却时间: {self._config.cooldown_seconds} 秒")
        print(f"{sep}\n")

    def _main_loop(self) -> None:
        """主循环：持续检查并处理任务"""
        while self._running:
            # 获取数据库统计
            db_stats = self._db_manager.get_statistics()
            print(
                f"\n📊 数据库状态: 总计={db_stats['total']}, "
                f"待下载={db_stats['pending']}, "
                f"成功={db_stats['success']}, "
                f"失败={db_stats['failed']}"
            )

            # 检查是否有待下载任务
            if db_stats["pending"] == 0:
                print(
                    f"✅ 没有待下载任务，{self._config.check_interval} 秒后再次检查..."
                )
                self._sleep_with_interrupt(self._config.check_interval)
                continue

            # 获取待下载任务
            tasks = self._db_manager.get_pending_tasks(limit=self._config.batch_size)
            if not tasks:
                print(f"⚠️  未能获取任务，{self._config.check_interval} 秒后重试...")
                self._sleep_with_interrupt(self._config.check_interval)
                continue

            # 处理每个任务
            for task in tasks:
                if not self._running:
                    print("⚠️  收到停止信号，中断任务处理")
                    break

                self._process_task(task)

                # 任务完成后倒计时（仅在有更多任务或将要循环检查时）
                if self._running and self._config.cooldown_seconds > 0:
                    self._countdown_with_progress(
                        self._config.cooldown_seconds, "任务完成，冷却倒计时"
                    )

            # 短暂延迟后继续
            if self._running:
                print(f"\n⏳ 等待 {self._config.check_interval} 秒后继续...")
                self._sleep_with_interrupt(self._config.check_interval)

    def _sleep_with_interrupt(self, seconds: int) -> None:
        """可中断的睡眠"""
        for _ in range(seconds):
            if not self._running:
                break
            time.sleep(1)

    def _countdown_with_progress(self, seconds: int, description: str = "等待中") -> None:
        """
        带进度条的倒计时

        Args:
            seconds: 倒计时秒数
            description: 描述文字
        """
        print(f"\n⏱️  {description}: {seconds} 秒")

        # 使用简单的字符进度条
        bar_length = 50  # 进度条长度
        for remaining in range(seconds, 0, -1):
            if not self._running:
                print("\n⚠️  倒计时被中断")
                break

            # 计算进度百分比
            progress = (seconds - remaining) / seconds
            filled_length = int(bar_length * progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            # 打印进度条（使用 \r 覆盖同一行）
            elapsed = seconds - remaining
            print(
                f"\r⏱️  [{bar}] {elapsed}/{seconds}s (剩余 {remaining}s)",
                end="",
                flush=True,
            )

            time.sleep(1)

        if self._running:
            # 完成时显示满进度条
            bar = "█" * bar_length
            print(f"\r⏱️  [{bar}] {seconds}/{seconds}s (完成)     ")
            print("✅ 等待完成，继续下一个任务\n")

    def _process_task(self, task: DownloadTask) -> None:
        """处理单个下载任务"""
        sep = "=" * 60
        print(f"\n{sep}")
        print("📥 开始处理任务")
        print(sep)
        print(f"ID: {task.id}")
        print(f"编号: {task.number}")
        print(f"标题: {task.title or 'N/A'}")
        print(f"提供商: {task.provider or 'N/A'}")
        print(f"M3U8: {task.m3u8_address}")
        print(f"{sep}\n")

        try:
            # 1. 创建下载配置
            filename = self._sanitize_filename(task.number)
            download_config = DownloadConfig(
                m3u8_url=task.m3u8_address,
                filename=filename,
                concurrent=self._config.concurrent,
                delay=self._config.delay,
            )

            # 2. 执行下载
            print(f"⬇️  开始下载: {filename}")
            _run_scrapy(download_config)
            print(f"✅ 下载完成: {filename}")

            # 3. 校验完整性
            print(f"\n🔍 开始校验: {filename}")
            download_dir = str(download_config.download_dir)
            is_complete, result = validate_downloads(download_dir)

            # 4. 更新数据库状态
            if is_complete:
                print(f"✅ 校验通过: {filename}")
                self._db_manager.update_task_status(
                    task.id, status=1, update_m3u8_time=True
                )
                self._stats.record_success()
                print("✅ 已更新数据库状态: status=1 (成功)")
            else:
                print(f"❌ 校验失败: {filename}")
                failed_count = len(result.get("failed_files", []))
                print(f"   失败文件数: {failed_count}")
                self._db_manager.update_task_status(
                    task.id, status=2, update_m3u8_time=True
                )
                self._stats.record_failure()
                print("⚠️  已更新数据库状态: status=2 (失败)")

        except Exception as e:
            print(f"❌ 处理任务失败 (ID={task.id}): {e}")
            import traceback

            traceback.print_exc()

            # 更新为失败状态
            self._db_manager.update_task_status(task.id, status=2)
            self._stats.record_failure()
            print("⚠️  已更新数据库状态: status=2 (异常失败)")

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名（移除不合法字符）"""
        name = filename.strip()
        for char in INVALID_FILENAME_CHARS:
            name = name.replace(char, "_")
        return name

    def _cleanup(self) -> None:
        """清理资源"""
        print("\n🧹 正在清理资源...")
        self._db_manager.close()
        self._stats.print_summary()
        print("👋 自动下载器已退出")


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
