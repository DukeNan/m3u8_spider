# Technology Stack

**Analysis Date:** 2026-03-20

## Languages

**Primary:**
- Python 3.14+ - 整个项目基于 Python 开发
- Bash - 用于同步脚本 `cli/sync_mp4.sh`

## Runtime

**Environment:**
- Python 3.13.0 (开发环境检测到的版本)
- 支持 Python 3.14+

**Package Manager:**
- uv - 现代 Python 包管理器
- Lockfile: `uv.lock` (存在)

## Frameworks

**Core:**
- Scrapy 2.11.0+ - Web 爬虫框架，用于下载 M3U8 视频片段
- m3u8 3.5.0+ - M3U8 播放列表解析库

**Data Processing:**
- tqdm 4.66.0+ - 进度条显示

**CLI & Utilities:**
- python-dotenv 1.0.0+ - .env 环境变量加载

**Database:**
- PyMySQL 1.1.0+ - MySQL 数据库驱动

**Testing/Linting:**
- ruff 0.15.0+ - 代码检查工具 (包含 linting 和 formatting)

**Optional Dependencies:**
- psycopg2-binary 2.9.0+ - PostgreSQL 驱动 (可选 `postgres` 组)
- crawl4ai 0.4.0+ - 网页爬取 (可选 `crawl` 组)

## External Tools

**Required:**
- FFmpeg 7.1+ - TS 片段合并为 MP4
  - 命令行工具，通过 `subprocess` 调用
  - 位置: `/opt/homebrew/bin/ffmpeg`

## Configuration

**Environment:**
- `.env` 文件 - MySQL 连接配置和其他环境变量
- `.env.example` - 配置模板
- 使用 `python-dotenv` 加载

**Build:**
- `pyproject.toml` - 项目配置和依赖定义
- `scrapy.cfg` - Scrapy 项目配置

**Linting/Formatting:**
- ruff 配置集成在 `pyproject.toml`
- 规则: E, F, W, I, UP, B
- 行长度限制: 100
- 目标 Python 版本: 3.14

## Key Dependencies Summary

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| scrapy | >=2.11.0 | M3U8 下载爬虫框架 |
| m3u8 | >=3.5.0 | M3U8 播放列表解析 |
| requests | >=2.31.0 | HTTP 请求 (Scrapy 依赖) |
| pymysql | >=1.1.0 | MySQL 数据库驱动 |
| python-dotenv | >=1.0.0 | .env 环境变量加载 |
| tqdm | >=4.66.0 | 进度条 |
| ruff | >=0.15.0 | 代码检查 |
| ffmpeg | 7.1+ | 视频合并 (系统依赖) |

## Platform Requirements

**Development:**
- Python 3.13+
- uv 包管理器
- FFmpeg (系统级安装)

**Production:**
- 相同 Python 版本
- FFmpeg 可执行文件在 PATH 中
- MySQL 数据库服务器 (用于自动下载守护进程)

---

*Stack analysis: 2026-03-20*
