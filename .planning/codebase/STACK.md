# Technology Stack

**Analysis Date:** 2026-03-29

## Languages

**Primary:**
- Python 3.14 - 整个项目使用，要求版本 `>=3.14`（见 `pyproject.toml` 第 14 行）

**Secondary:**
- Shell (Bash) - 用于 MP4 同步脚本 `cli/sync_mp4.sh`

## Runtime

**Environment:**
- Python 虚拟环境（`.venv/`）
- 开发环境使用 `uv` 作为包管理器（版本 0.10.0）

**Package Manager:**
- `uv` - 项目安装命令: `source .venv/bin/activate && uv pip install -e .`
- Lockfile: 无（使用 `uv` 管理依赖）

## Frameworks

**Core:**
- Scrapy 2.11+ - 爬虫框架，用于下载 M3U8 视频片段（见 `scrapy_project/m3u8_spider/`）
- Twisted - Scrapy 的底层异步引擎，使用 `AsyncioSelectorReactor`（见 `settings.py` 第 89 行）

**Testing:**
- 无专门测试框架，通过运行模块验证

**Build/Dev:**
- setuptools - 构建后端（`pyproject.toml` 第 1-3 行）
- Ruff 0.15+ - 代码格式化和 lint（`pyproject.toml` 第 19 行）

## Key Dependencies

**Critical:**
- `m3u8` 3.5+ - M3U8 播放列表解析库，用于解析 HLS 视频片段（见 `spiders/m3u8_downloader.py` 第 14 行）
- `pymysql` 1.1+ - MySQL 数据库驱动，用于守护进程的数据库操作（见 `database/manager.py` 第 13 行）
- `requests` 2.31+ - HTTP 请求库，辅助用途
- `python-dotenv` 1.0+ - 环境变量加载（见 `config.py` 第 20 行）
- `tqdm` 4.66+ - 进度条显示，用于守护进程冷却倒计时（见 `auto_downloader.py` 第 25 行）

**Infrastructure:**
- FFmpeg - 外部依赖，用于 TS 文件合并为 MP4（见 `utils/merger.py`，需系统安装）
- Playwright - 可选依赖，通过 `crawl4ai` 用于 M3U8 URL 刷新功能

**Optional:**
- `crawl4ai` 0.4+ - 网页爬取库，用于 M3U8 URL 刷新守护进程（见 `pyproject.toml` 第 28 行 `[project.optional-dependencies]`）
- `psycopg2-binary` 2.9+ - PostgreSQL 驱动（可选，见 `pyproject.toml` 第 26 行）

## Configuration

**Environment:**
- `.env` 文件存储敏感配置（MySQL 连接信息、可覆盖的默认值）
- 配置加载: `m3u8_spider/config.py` 使用 `python-dotenv` 自动加载项目根目录 `.env`
- 配置模板: `env.example` 提供配置示例

**Build:**
- `pyproject.toml` - 项目构建配置、依赖、CLI 入口点定义
- `scrapy_project/m3u8_spider/settings.py` - Scrapy 爬虫配置

## Platform Requirements

**Development:**
- Python 3.14+ 环境
- FFmpeg 已安装（用于合并测试）
- MySQL 数据库（用于守护进程开发测试）

**Production:**
- 支持 macOS/Linux/Windows
- 远程 Jellyfin 媒体服务器（可选，用于 MP4 同步）
- MySQL 数据库（用于批量下载守护进程）

## CLI Entry Points

通过 `pyproject.toml` 第 29-33 行定义的可执行命令：

| 命令 | 模块 | 用途 |
|------|------|------|
| `m3u8-download` | `cli/main.py` | 单次下载入口 |
| `m3u8-daemon` | `cli/daemon.py` | 批量下载守护进程 |
| `m3u8-batch-merge` | `cli/batch_merge.py` | 批量合并 MP4 |
| `m3u8-refresh` | `cli/m3u8_refresh_daemon.py` | M3U8 URL 刷新守护进程 |

---

*Stack analysis: 2026-03-29*