#!/usr/bin/env python3
"""将 SQLite3 数据导入到 PostgreSQL 16 的脚本。

用法:
    python sqlite_to_postgres.py <sqlite_path> [--pg-url URL]
    
环境变量 (当未提供 --pg-url 时):
    PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE

依赖:
    pip install psycopg2-binary
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import Json, execute_values
except ImportError:
    print("请安装 psycopg2: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


# PostgreSQL 建表语句 (来自 aaa.txt)
PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS actor_metadata (
    id text,
    name text,
    provider text,
    homepage text,
    summary text,
    hobby text,
    skill text,
    blood_type text,
    cup_size text,
    measurements text,
    nationality text,
    height integer,
    aliases text[],
    images text[],
    birthday date,
    debut_date date,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (id, provider)
);

CREATE TABLE IF NOT EXISTS movie_metadata (
    id text,
    number text,
    title text,
    summary text,
    provider text,
    homepage text,
    director text,
    actors text[],
    thumb_url text,
    big_thumb_url text,
    cover_url text,
    big_cover_url text,
    preview_video_url text,
    preview_video_hls_url text,
    preview_images text[],
    maker text,
    label text,
    series text,
    genres text[],
    score real,
    runtime integer,
    release_date date,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (id, provider)
);

CREATE TABLE IF NOT EXISTS movie_reviews (
    id text,
    provider text,
    reviews jsonb,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (id, provider)
);
"""


def _parse_json_or_array(value: str | None) -> list[str] | None:
    """将 SQLite 中的 JSON/逗号分隔字符串解析为 Python list，供 PostgreSQL text[] 使用。"""
    if value is None or value == "":
        return None
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return [str(parsed)]
    except json.JSONDecodeError:
        # 兼容逗号分隔格式
        return [s.strip() for s in str(value).split(",") if s.strip()] or None


def _parse_json_for_pg(value: str | None):
    """将 SQLite 中的 JSON 字符串解析为 psycopg2 Json 对象，供 PostgreSQL jsonb 使用。"""
    if value is None or value == "":
        return None
    try:
        return Json(json.loads(value))
    except json.JSONDecodeError:
        return Json(value) if value else None


def get_pg_connection(url: str | None = None):
    """获取 PostgreSQL 连接。"""
    if url:
        return psycopg2.connect(url)
    import os

    host = os.environ.get("PG_HOST", "localhost")
    port = os.environ.get("PG_PORT", "5432")
    user = os.environ.get("PG_USER", "postgres")
    password = os.environ.get("PG_PASSWORD", "")
    database = os.environ.get("PG_DATABASE", "postgres")
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=database,
    )


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    table: str,
    columns: list[str],
    array_columns: set[str],
    json_columns: set[str],
) -> int:
    """迁移单个表。"""
    cur_sqlite = sqlite_conn.cursor()
    try:
        cur_sqlite.execute(f"SELECT * FROM {table}")
        rows = cur_sqlite.fetchall()
        col_names = [d[0] for d in cur_sqlite.description] if cur_sqlite.description else []
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            raise ValueError(f"SQLite 中不存在表 {table}") from e
        raise
    finally:
        cur_sqlite.close()

    if not rows:
        return 0

    col_idx = {name: i for i, name in enumerate(col_names)}
    # 只迁移 SQLite 中存在的列
    valid_columns = [c for c in columns if c in col_idx]
    if not valid_columns:
        raise ValueError(f"表 {table} 无匹配列")
    placeholders = ", ".join(["%s"] * len(valid_columns))
    cols_str = ", ".join(valid_columns)

    def transform_row(row: tuple) -> tuple:
        out = []
        for col in valid_columns:
            idx = col_idx.get(col)
            if idx is None:
                out.append(None)
                continue
            val = row[idx] if idx < len(row) else None
            if col in array_columns and val is not None:
                out.append(_parse_json_or_array(val) if isinstance(val, str) else val)
            elif col in json_columns and val is not None:
                if isinstance(val, str):
                    out.append(_parse_json_for_pg(val))
                else:
                    out.append(Json(val) if val is not None else None)
            else:
                out.append(val)
        return tuple(out)

    transformed = [transform_row(r) for r in rows]
    insert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    with pg_conn.cursor() as cur:
        execute_values(cur, insert_sql, transformed, page_size=500)

    pg_conn.commit()
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="将 SQLite3 数据导入 PostgreSQL 16")
    parser.add_argument("sqlite_path", type=Path, help="SQLite 数据库文件路径")
    parser.add_argument(
        "--pg-url",
        type=str,
        default=None,
        help="PostgreSQL 连接 URL (如 postgresql://user:pass@host:5432/dbname)",
    )
    parser.add_argument("--drop-tables", action="store_true", help="导入前删除已存在的表（慎用）")
    args = parser.parse_args()

    if not args.sqlite_path.exists():
        print(f"错误: SQLite 文件不存在: {args.sqlite_path}", file=sys.stderr)
        return 1

    sqlite_conn = sqlite3.connect(args.sqlite_path)
    pg_conn = get_pg_connection(args.pg_url)

    try:
        with pg_conn.cursor() as cur:
            if args.drop_tables:
                for t in ("actor_metadata", "movie_metadata", "movie_reviews"):
                    cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
                pg_conn.commit()
            cur.execute(PG_SCHEMA)
        pg_conn.commit()

        tables_config = [
            (
                "actor_metadata",
                [
                    "id", "name", "provider", "homepage", "summary", "hobby", "skill",
                    "blood_type", "cup_size", "measurements", "nationality", "height",
                    "aliases", "images", "birthday", "debut_date", "created_at", "updated_at",
                ],
                {"aliases", "images"},
                set(),
            ),
            (
                "movie_metadata",
                [
                    "id", "number", "title", "summary", "provider", "homepage", "director",
                    "actors", "thumb_url", "big_thumb_url", "cover_url", "big_cover_url",
                    "preview_video_url", "preview_video_hls_url", "preview_images",
                    "maker", "label", "series", "genres", "score", "runtime",
                    "release_date", "created_at", "updated_at",
                ],
                {"actors", "preview_images", "genres"},
                set(),
            ),
            (
                "movie_reviews",
                ["id", "provider", "reviews", "created_at", "updated_at"],
                set(),
                {"reviews"},
            ),
        ]

        total = 0
        for table, columns, array_cols, json_cols in tables_config:
            try:
                n = migrate_table(
                    sqlite_conn, pg_conn, table, columns, array_cols, json_cols
                )
                print(f"  {table}: {n} 行")
                total += n
            except Exception as e:
                print(f"  {table}: 跳过 ({e})", file=sys.stderr)

        print(f"\n完成，共导入 {total} 行")
        return 0

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    sys.exit(main())
