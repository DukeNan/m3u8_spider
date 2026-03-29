# Codebase Structure

**Analysis Date:** 2026-03-29

## Directory Layout

```
m3u8_spider/
├── cli/                    # CLI 入口脚本
├── m3u8_spider/            # 核心包
│   ├── core/               # 下载/校验/恢复核心逻辑
│   ├── automation/         # 守护进程协调器
│   ├── database/           # MySQL 数据库操作
│   └── utils/              # 合并/迁移等工具
├── scrapy_project/         # Scrapy 爬虫项目
│   └── m3u8_spider/        # Scrapy 包
│       └── spiders/        # Spider 定义
├── movies/                 # 下载输出目录 (TS 片段)
├── mp4/                    # 合并后的 MP4 文件
├── logs/                   # 下载日志
├── utils/                  # 外部脚本 (如 sync_mp4.sh)
├── .planning/              # 规划文档目录
│   └── codebase/           # 代码库分析文档
└── .claude/                # Claude 配置目录
```

## Directory Purposes

**cli/:**
- Purpose: CLI 入口点，解析命令行参数并调用核心模块
- Contains: 4 个入口脚本 + 1 个 shell 脚本
- Key files: `main.py` (单次下载), `daemon.py` (自动下载守护进程), `m3u8_refresh_daemon.py` (URL 刷新守护进程), `batch_merge.py` (批量合并), `sync_mp4.sh` (同步到 Jellyfin)

**m3u8_spider/:**
- Purpose: 核心包，提供下载、校验、恢复、数据库操作等功能
- Contains: 配置、日志、核心模块、自动化模块、数据库模块、工具模块
- Key files: `config.py` (统一配置), `logger.py` (日志配置), `__init__.py`

**m3u8_spider/core/:**
- Purpose: 下载核心逻辑，包括配置管理、恢复流程、校验
- Contains: 4 个模块
- Key files: `downloader.py` (`DownloadConfig` + `run_scrapy`), `recovery.py` (`recover_download` 协调器), `validator.py` (校验逻辑), `m3u8_fetcher.py` (页面 M3U8 抓取)

**m3u8_spider/automation/:**
- Purpose: 守护进程协调器，管理任务队列和下载循环
- Contains: 2 个模块
- Key files: `auto_downloader.py` (`AutoDownloader` 类), `m3u8_refresher.py` (`M3U8Refresher` 类)

**m3u8_spider/database/:**
- Purpose: MySQL 数据库操作
- Contains: 1 个模块
- Key files: `manager.py` (`DatabaseManager` + `DownloadTask`)

**m3u8_spider/utils/:**
- Purpose: 辅助工具，TS 合并、数据库迁移
- Contains: 3 个模块
- Key files: `merger.py` (`MP4Merger` + FFmpeg 合并), `migration.py` (数据库迁移)

**scrapy_project/:**
- Purpose: Scrapy 项目目录，subprocess 运行时的工作目录
- Contains: Scrapy 包 + 临时下载目录
- Key files: 无直接入口，由 `run_scrapy()` 在此目录下执行

**scrapy_project/m3u8_spider/:**
- Purpose: Scrapy 爬虫包定义
- Contains: Spider、Pipeline、Settings、Items、Extensions
- Key files: `spiders/m3u8_downloader.py` (核心 Spider), `pipelines.py` (文件下载 Pipeline), `settings.py` (Scrapy 配置), `items.py` (M3U8Item 定义), `extensions.py` (文件日志扩展), `logformatter.py` (日志格式化)

**scrapy_project/m3u8_spider/spiders/:**
- Purpose: Spider 定义
- Contains: 1 个 Spider
- Key files: `m3u8_downloader.py` (`M3U8DownloaderSpider`)

**movies/:**
- Purpose: 下载输出目录，每个视频一个子目录
- Contains: TS 片段 + 元数据文件
- Generated: Yes (下载过程生成)
- Committed: No (通常不提交到 git)

**mp4/:**
- Purpose: 合并后的 MP4 文件输出目录
- Contains: MP4 文件
- Generated: Yes (合并过程生成)
- Committed: No

**logs/:**
- Purpose: 下载日志文件目录
- Contains: `<filename>.log` 日志文件
- Generated: Yes (下载过程生成)
- Committed: No

**utils/:**
- Purpose: 外部辅助脚本
- Contains: Shell 脚本
- Key files: `sync_mp4.sh` (rsync 同步到 Jellyfin)

**.planning/codebase/:**
- Purpose: 代码库分析文档存储
- Contains: STACK.md, ARCHITECTURE.md, STRUCTURE.md 等分析文档
- Generated: Yes (GSD 工具生成)
- Committed: Yes

## Key File Locations

**Entry Points:**
- `cli/main.py`: 单次下载入口 (`m3u8-download`)
- `cli/daemon.py`: 自动下载守护进程入口 (`m3u8-daemon`)
- `cli/m3u8_refresh_daemon.py`: M3U8 URL 刷新守护进程入口 (`m3u8-refresh`)
- `cli/batch_merge.py`: 批量合并入口 (`m3u8-batch-merge`)
- `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`: Scrapy Spider

**Configuration:**
- `m3u8_spider/config.py`: 统一配置管理
- `scrapy_project/m3u8_spider/settings.py`: Scrapy 配置
- `.env`: 环境变量配置 (MySQL 等)
- `env.example`: 配置模板
- `pyproject.toml`: 项目元数据和入口点定义

**Core Logic:**
- `m3u8_spider/core/downloader.py`: `DownloadConfig` + `run_scrapy()`
- `m3u8_spider/core/recovery.py`: `recover_download()` 恢复协调器
- `m3u8_spider/core/validator.py`: `validate_downloads()` 校验逻辑
- `m3u8_spider/core/m3u8_fetcher.py`: `fetch_m3u8_from_page()` 页面抓取

**Database:**
- `m3u8_spider/database/manager.py`: `DatabaseManager` + `DownloadTask`

**Automation:**
- `m3u8_spider/automation/auto_downloader.py`: `AutoDownloader` 自动下载协调器
- `m3u8_spider/automation/m3u8_refresher.py`: `M3U8Refresher` URL 刷新协调器

**Scrapy Components:**
- `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`: `M3U8DownloaderSpider`
- `scrapy_project/m3u8_spider/pipelines.py`: `M3U8FilePipeline` 文件下载
- `scrapy_project/m3u8_spider/items.py`: `M3U8Item` 定义
- `scrapy_project/m3u8_spider/extensions.py`: `M3U8FileLogExtension` 文件日志
- `scrapy_project/m3u8_spider/logformatter.py`: `M3U8LogFormatter` 日志格式化

**Testing:**
- 无专门的 tests 目录，通过 `python -m` 运行模块测试

**Utilities:**
- `m3u8_spider/utils/merger.py`: `MP4Merger` + `merge_ts_files()`
- `cli/sync_mp4.sh`: rsync 同步脚本

**Logging:**
- `m3u8_spider/logger.py`: `get_logger()` + `setup_logger()`

## Naming Conventions

**Files:**
- 模块文件: 小写 + 下蛇线，如 `downloader.py`, `auto_downloader.py`
- CLI 入口: 简短名称，如 `main.py`, `daemon.py`
- Shell 脚本: 下蛇线，如 `sync_mp4.sh`

**Directories:**
- 包目录: 小写，如 `cli`, `core`, `automation`
- 输出目录: 功能命名，如 `movies`, `mp4`, `logs`

**Classes:**
- 大驼峰，如 `DownloadConfig`, `AutoDownloader`, `M3U8DownloaderSpider`
- 协调器/管理器: `*Manager`, `*Downloader`, `*Refresher`
- 数据模型: `*Result`, `*Info`, `*Task`, `*Config`

**Functions:**
- 下蛇线，如 `run_scrapy`, `recover_download`, `validate_downloads`
- 工厂函数: `create_*`, 如 `create_auto_downloader`
- 模块入口: `main()`

**Dataclasses:**
- 配置: `*Config`
- 结果: `*Result`
- 信息: `*Info`
- 任务: `*Task`

## Where to Add New Code

**New Feature (下载相关):**
- 核心逻辑: `m3u8_spider/core/`
- 如需修改下载流程: `m3u8_spider/core/downloader.py`
- 如需修改校验逻辑: `m3u8_spider/core/validator.py`
- 如需修改恢复流程: `m3u8_spider/core/recovery.py`

**New Feature (自动化相关):**
- 自动化逻辑: `m3u8_spider/automation/`
- 新守护进程: 创建新模块 + 对应 CLI 入口

**New CLI Command:**
- CLI 脚本: `cli/`
- 注册入口点: `pyproject.toml` 的 `[project.scripts]`

**New Spider/Pipeline:**
- Spider: `scrapy_project/m3u8_spider/spiders/`
- Pipeline: `scrapy_project/m3u8_spider/pipelines.py`
- 注册 Pipeline: `scrapy_project/m3u8_spider/settings.py` 的 `ITEM_PIPELINES`

**New Database Operation:**
- 数据库操作: `m3u8_spider/database/manager.py`
- 新数据模型: 同文件内定义 dataclass

**New Utility:**
- 工具函数: `m3u8_spider/utils/`
- Shell 脚本: `cli/` 或 `utils/`

**New Configuration:**
- 配置项: `m3u8_spider/config.py`
- 环境变量: `.env` + `env.example`

**New Tests:**
- 当前无 tests 目录
- 建议: 创建 `tests/` 目录，使用 pytest

## Special Directories

**scrapy_project/:**
- Purpose: Scrapy 项目运行目录
- Generated: No
- Committed: Yes
- 特殊: `run_scrapy()` 通过 `cwd=scrapy_project` 在此目录执行

**movies/<name>/:**
- Purpose: 单个视频下载目录
- Generated: Yes (下载时创建)
- Committed: No
- Contains: TS 片段 + `playlist.txt` + `encryption_info.json` + `content_lengths.json` + `encryption.key` (若加密)

**.venv/:**
- Purpose: Python 虚拟环境
- Generated: Yes (`uv venv` 或 `python -m venv`)
- Committed: No

**.ruff_cache/:**
- Purpose: Ruff linter 缓存
- Generated: Yes (ruff 运行时)
- Committed: No

**__pycache__/:**
- Purpose: Python 字节码缓存
- Generated: Yes (Python 运行时)
- Committed: No

---

*Structure analysis: 2026-03-29*