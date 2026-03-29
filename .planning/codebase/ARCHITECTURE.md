# Architecture

**Analysis Date:** 2026-03-29

## Pattern Overview

**Overall:** 分层架构 + subprocess 调用模式

**Key Characteristics:**
- CLI 层与核心层分离，通过 subprocess 调用 Scrapy 爬虫
- 恢复流程作为协调器，串联下载、校验、重试
- 守护进程独立运行，每个下载任务启动独立 subprocess
- 数据库层作为数据源，为守护进程提供任务队列

## Layers

**CLI 层 (Command Line Interface):**
- Purpose: 解析命令行参数、组装配置、调用核心模块
- Location: `cli/`
- Contains: 入口脚本 (`main.py`, `daemon.py`, `batch_merge.py`, `m3u8_refresh_daemon.py`)
- Depends on: `m3u8_spider.core`, `m3u8_spider.automation`, `m3u8_spider.config`
- Used by: 用户命令行调用 (`m3u8-download`, `m3u8-daemon`)

**核心层 (Core Layer):**
- Purpose: 下载配置管理、恢复流程协调、校验逻辑
- Location: `m3u8_spider/core/`
- Contains: `downloader.py`, `recovery.py`, `validator.py`, `m3u8_fetcher.py`
- Depends on: `m3u8_spider.config`, Scrapy subprocess
- Used by: CLI 层、自动化层

**自动化层 (Automation Layer):**
- Purpose: 守护进程协调器，管理任务队列和下载循环
- Location: `m3u8_spider/automation/`
- Contains: `auto_downloader.py`, `m3u8_refresher.py`
- Depends on: `m3u8_spider.core`, `m3u8_spider.database`
- Used by: 守护进程 CLI (`cli/daemon.py`, `cli/m3u8_refresh_daemon.py`)

**数据库层 (Database Layer):**
- Purpose: MySQL 连接管理和 CRUD 操作
- Location: `m3u8_spider/database/`
- Contains: `manager.py`
- Depends on: `pymysql`
- Used by: 自动化层

**工具层 (Utils Layer):**
- Purpose: TS 文件合并、数据库迁移等辅助功能
- Location: `m3u8_spider/utils/`
- Contains: `merger.py`, `migration.py`
- Depends on: `ffmpeg` (外部依赖)
- Used by: CLI 层、批处理脚本

**Scrapy 项目层 (Scrapy Project Layer):**
- Purpose: 实际执行 M3U8 解析和 TS 下载的爬虫
- Location: `scrapy_project/m3u8_spider/`
- Contains: `spiders/m3u8_downloader.py`, `pipelines.py`, `settings.py`, `items.py`
- Depends on: Scrapy 框架
- Used by: 核心层通过 subprocess 调用

## Data Flow

**单次下载流程:**

```
用户命令 (m3u8-download)
    │
    ▼
cli/main.py: 解析参数 → DownloadConfig
    │
    ▼
core/recovery.py: recover_download()
    │
    ├─► 检测缺失元数据
    │       │
    │       ▼
    │   core/downloader.py: run_scrapy(metadata_only=True)
    │       │
    │       ▼ subprocess
    │   scrapy_project/spider: 解析 M3U8 → 下载密钥
    │
    ├─► 校验完整性
    │       │
    │       ▼
    │   core/validator.py: validate_downloads()
    │
    └─► 重试失败片段 (最多 3 轮)
            │
            ▼
        core/downloader.py: run_scrapy(retry_urls=...)
            │
            ▼ subprocess
        scrapy_project/spider: 仅下载指定 TS
```

**守护进程自动下载流程:**

```
m3u8-daemon 启动
    │
    ▼
cli/daemon.py: 加载 MySQL 配置
    │
    ▼
automation/auto_downloader.py: AutoDownloader.run()
    │
    ▼ 主循环
database/manager.py: get_pending_tasks(status=0)
    │
    ▼
每个任务:
    │
    ├─► core/recovery.py: recover_download()
    │       (完整下载流程)
    │
    └─► database/manager.py: update_task_status(status=1/2)
    │
    ▼
冷却等待 → 下一轮检查
```

**M3U8 URL 刷新流程:**

```
m3u8-refresh 启动
    │
    ▼
cli/m3u8_refresh_daemon.py
    │
    ▼
automation/m3u8_refresher.py: M3U8Refresher.run()
    │
    ▼ 主循环
database/manager.py: get_tasks_for_m3u8_refresh()
    │
    ▼
每个任务:
    │
    ├─► core/m3u8_fetcher.py: fetch_m3u8_from_page(page_url)
    │       │
    │       ▼ crawl4ai (可选依赖)
    │   浏览器爬取 → 正则提取 M3U8 URL
    │
    └─► database/manager.py: update_m3u8_address()
```

**Scrapy 爬虫内部流程:**

```
spider.start_requests()
    │
    ├─► Request(m3u8_url) → parse_m3u8
    │       │
    │       ▼
    │   解析 M3U8 → 检测加密 → 保存 playlist.txt
    │       │
    │       ├─► 若加密 → Request(key_uri) → 保存 encryption.key
    │       │
    │       ▼
    │   遍历 segments → yield M3U8Item(url, filename, directory)
    │
    ▼
pipelines.py: M3U8FilePipeline
    │
    ├─► get_media_requests() → Request(url)
    │
    ├─► media_downloaded() → 记录 Content-Length
    │
    └─► close_spider() → 保存 content_lengths.json
```

**State Management:**
- 无全局状态，每个下载任务独立 subprocess
- 通过文件系统传递状态 (`playlist.txt`, `content_lengths.json`, `encryption_info.json`)
- 数据库维护任务状态 (`status: 0=待处理, 1=成功, 2=失败`)

## Key Abstractions

**DownloadConfig (下载配置):**
- Purpose: 封装下载参数，提供路径解析和验证
- Examples: `m3u8_spider/core/downloader.py`
- Pattern: dataclass + frozen，属性计算路径
- Key properties: `sanitized_filename`, `download_dir`, `scrapy_project_dir`

**DownloadTask (数据库任务模型):**
- Purpose: 映射数据库 `movie_info` 表记录
- Examples: `m3u8_spider/database/manager.py`
- Pattern: dataclass，包含 `id`, `number`, `m3u8_address`, `status`, `url`

**M3U8Item (Scrapy 下载项):**
- Purpose: Spider 产出的下载请求项
- Examples: `scrapy_project/m3u8_spider/items.py`
- Pattern: scrapy.Item，字段: `url`, `filename`, `directory`, `segment_index`

**ValidationResult (校验结果):**
- Purpose: 封装下载完整性校验结果
- Examples: `m3u8_spider/core/validator.py`
- Pattern: dataclass，提供 `is_complete` 属性和 `to_legacy_dict()` 方法

**RecoveryResult (恢复结果):**
- Purpose: 封装恢复流程的最终状态
- Examples: `m3u8_spider/core/recovery.py`
- Pattern: dataclass，记录重试轮次历史

**EncryptionInfo (加密信息):**
- Purpose: M3U8 加密检测结果
- Examples: `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`
- Pattern: dataclass + `to_dict()` 序列化

## Entry Points

**CLI 入口点:**
- Location: `cli/main.py:main()`
- Triggers: `m3u8-download` 命令
- Responsibilities: 解析参数 → 调用 `recover_download()` → 打印后续步骤

**守护进程入口点:**
- Location: `cli/daemon.py:main()`
- Triggers: `m3u8-daemon` 命令
- Responsibilities: 加载 MySQL 配置 → 创建 `AutoDownloader` → 运行主循环

**M3U8 刷新入口点:**
- Location: `cli/m3u8_refresh_daemon.py:main()`
- Triggers: `m3u8-refresh` 命令
- Responsibilities: 加载配置 → 创建 `M3U8Refresher` → 运行刷新循环

**批量合并入口点:**
- Location: `cli/batch_merge.py:main()`
- Triggers: `m3u8-batch-merge` 命令
- Responsibilities: 遍历 `movies/` → 校验 → 合并 → 删除源目录

**模块入口点 (python -m):**
- `python -m m3u8_spider.core.validator <video_name>` - 校验下载
- `python -m m3u8_spider.utils.merger <video_name>` - 合并为 MP4

## Error Handling

**Strategy:** 分层处理，底层抛出，上层捕获并记录

**Patterns:**
- CLI 层: 捕获异常 → 打印错误 → `sys.exit(1)`
- 守护进程: 捕获异常 → 更新数据库状态为失败 → 继续下一任务
- Scrapy 爬虫: 解析失败 → 回退到手动正则解析
- 数据库层: 连接失败 → 重试机制 (最多 3 次)

**重试机制:**
- 数据库连接: `max_retries=3`, `retry_delay=2.0` 秒
- 下载恢复: `max_retry_rounds=3`，每轮仅重下失败 TS

## Cross-Cutting Concerns

**Logging:** `m3u8_spider/logger.py`
- 使用 Python `logging` 模块
- 支持控制台 + 文件双输出
- Scrapy 通过 `M3U8FileLogExtension` 添加文件日志

**Validation:** `m3u8_spider/core/validator.py`
- 文件数量校验 (playlist vs 实际 TS)
- Content-Length 校验 (允许 ±1% 或 ±1KB)
- 零字节文件检测

**Configuration:** `m3u8_spider/config.py`
- 统一配置管理，从 `.env` 加载
- 环境变量覆盖默认值
- MySQL 配置必须从环境变量读取

**Signal Handling:**
- 守护进程注册 `SIGINT`/`SIGTERM` 处理器
- 第一次信号: 优雅退出标志
- 第二次信号: 强制退出

---

*Architecture analysis: 2026-03-29*