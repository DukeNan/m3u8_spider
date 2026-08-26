"""从文本文件导入影片页面地址。"""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

from m3u8_spider.config import get_mysql_config
from m3u8_spider.database.manager import DatabaseManager


def read_records(path: Path) -> list[tuple[str, str]]:
    """读取并校验每行一个 NUMBER URL 的 UTF-8 文本文件。"""
    records: list[tuple[str, str]] = []
    numbers: set[str] = set()

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"第 {line_number} 行应为: NUMBER URL")

        number, url = parts
        parsed = urlparse(url)
        if not number or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"第 {line_number} 行包含无效的编号或 URL")
        if number in numbers:
            raise ValueError(f"第 {line_number} 行的编号重复: {number}")

        numbers.add(number)
        records.append((number, url))

    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量导入 movie_info 页面 URL")
    parser.add_argument("input", type=Path, help="每行 NUMBER URL 的 UTF-8 文本文件")
    parser.add_argument("--dry-run", action="store_true", help="只校验并显示记录数，不写入数据库")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_records(args.input)
    if not records:
        raise SystemExit("没有可导入的记录")
    if args.dry_run:
        print(f"校验通过：{len(records)} 条记录")
        return

    mysql = get_mysql_config()
    manager = DatabaseManager(
        host=mysql["MYSQL_HOST"],
        port=mysql["MYSQL_PORT"],
        user=mysql["MYSQL_USER"],
        password=mysql["MYSQL_PASSWORD"],
        database=mysql["MYSQL_DATABASE"],
    )
    if not manager.connect():
        raise SystemExit("无法连接数据库")
    try:
        inserted, skipped = manager.insert_missing_page_urls(records)
    finally:
        manager.close()
    print(f"完成：新增 {inserted} 条，跳过 {skipped} 条已有编号")
