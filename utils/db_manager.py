#!/usr/bin/env python3
"""
MySQL 数据库管理模块
负责连接数据库、查询待下载任务、更新任务状态
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

from utils.logger import get_logger

# 初始化 logger
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class DownloadTask:
    """下载任务数据模型"""

    id: int
    number: str
    m3u8_address: str
    status: int
    title: str | None = None
    provider: str | None = None

    def __repr__(self) -> str:
        return (
            f"DownloadTask(id={self.id}, number={self.number!r}, status={self.status})"
        )


# ---------------------------------------------------------------------------
# 数据库管理器
# ---------------------------------------------------------------------------


class DatabaseManager:
    """MySQL 数据库管理器，负责连接池和所有数据库操作"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        """
        初始化数据库管理器

        Args:
            host: MySQL 主机地址
            port: MySQL 端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            max_retries: 连接失败最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self._config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": True,
        }
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._connection: pymysql.Connection | None = None

    def connect(self) -> bool:
        """
        建立数据库连接（带重试机制）

        Returns:
            连接成功返回 True，失败返回 False
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                self._connection = pymysql.connect(**self._config)
                logger.info(
                    f"✅ 数据库连接成功: {self._config['host']}:{self._config['port']}/{self._config['database']}"
                )
                return True
            except pymysql.Error as e:
                logger.error(
                    f"❌ 数据库连接失败 (尝试 {attempt}/{self._max_retries}): {e}"
                )
                if attempt < self._max_retries:
                    logger.warning(f"   {self._retry_delay} 秒后重试...")
                    time.sleep(self._retry_delay)
                else:
                    logger.error("   已达到最大重试次数，放弃连接")
                    return False
        return False

    def close(self) -> None:
        """关闭数据库连接"""
        if self._connection:
            try:
                self._connection.close()
                logger.info("✅ 数据库连接已关闭")
            except Exception as e:
                logger.warning(f"⚠️  关闭数据库连接时出错: {e}")
            finally:
                self._connection = None

    def _ensure_connection(self) -> bool:
        """
        确保数据库连接可用，若断开则重连

        Returns:
            连接可用返回 True，否则返回 False
        """
        if not self._connection:
            return self.connect()

        try:
            self._connection.ping(reconnect=True)
            return True
        except Exception:
            logger.warning("⚠️  数据库连接已断开，尝试重连...")
            return self.connect()

    def get_pending_tasks(self, limit: int = 10) -> list[DownloadTask]:
        """
        查询待下载的任务（status=0）

        Args:
            limit: 单次查询的最大任务数

        Returns:
            待下载任务列表
        """
        if not self._ensure_connection() or not self._connection:
            return []

        try:
            with self._connection.cursor() as cursor:
                sql = """
                    SELECT id, number, m3u8_address, status, title, provider
                    FROM movie_info
                    WHERE status = 0 AND m3u8_address IS NOT NULL AND m3u8_address != ''
                    ORDER BY id ASC
                    LIMIT %s
                """
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()

                tasks = []
                for row in rows:
                    task = DownloadTask(
                        id=row["id"],
                        number=row["number"],
                        m3u8_address=row["m3u8_address"],
                        status=row["status"],
                        title=row.get("title"),
                        provider=row.get("provider"),
                    )
                    tasks.append(task)
                return tasks
        except pymysql.Error as e:
            logger.error(f"❌ 查询待下载任务失败: {e}")
            return []

    def update_task_status(
        self,
        task_id: int,
        status: int,
        update_m3u8_time: bool = False,
    ) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 新状态 (0=未下载, 1=下载成功, 2=下载失败)
            update_m3u8_time: 是否同时更新 m3u8_update_time

        Returns:
            更新成功返回 True，失败返回 False
        """
        if not self._ensure_connection() or not self._connection:
            return False

        try:
            with self._connection.cursor() as cursor:
                if update_m3u8_time:
                    sql = """
                        UPDATE movie_info
                        SET status = %s, m3u8_update_time = %s
                        WHERE id = %s
                    """
                    cursor.execute(sql, (status, datetime.now(), task_id))
                else:
                    sql = """
                        UPDATE movie_info
                        SET status = %s
                        WHERE id = %s
                    """
                    cursor.execute(sql, (status, task_id))

                return cursor.rowcount > 0
        except pymysql.Error as e:
            logger.error(f"❌ 更新任务状态失败 (ID={task_id}): {e}")
            return False

    def get_task_by_id(self, task_id: int) -> DownloadTask | None:
        """
        根据 ID 查询单个任务

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，不存在则返回 None
        """
        if not self._ensure_connection() or not self._connection:
            return None

        try:
            with self._connection.cursor() as cursor:
                sql = """
                    SELECT id, number, m3u8_address, status, title, provider
                    FROM movie_info
                    WHERE id = %s
                """
                cursor.execute(sql, (task_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return DownloadTask(
                    id=row["id"],
                    number=row["number"],
                    m3u8_address=row["m3u8_address"],
                    status=row["status"],
                    title=row.get("title"),
                    provider=row.get("provider"),
                )
        except pymysql.Error as e:
            logger.error(f"❌ 查询任务失败 (ID={task_id}): {e}")
            return None

    def get_statistics(self) -> dict[str, int]:
        """
        获取下载统计信息

        Returns:
            统计字典 {total, pending, success, failed}
        """
        if not self._ensure_connection() or not self._connection:
            return {"total": 0, "pending": 0, "success": 0, "failed": 0}

        try:
            with self._connection.cursor() as cursor:
                sql = """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) as failed
                    FROM movie_info
                    WHERE m3u8_address IS NOT NULL AND m3u8_address != ''
                """
                cursor.execute(sql)
                row = cursor.fetchone()

                return {
                    "total": row["total"] or 0,
                    "pending": row["pending"] or 0,
                    "success": row["success"] or 0,
                    "failed": row["failed"] or 0,
                }
        except pymysql.Error as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {"total": 0, "pending": 0, "success": 0, "failed": 0}

    def __enter__(self) -> DatabaseManager:
        """上下文管理器：进入"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器：退出"""
        self.close()
