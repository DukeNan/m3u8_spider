# Architecture

**Analysis Date:** 2026-03-20

## Pattern Overview

**Overall:** Layered Architecture with Subprocess Integration

**Key Characteristics:**
- **Core/CLI separation**: High-level orchestration in `cli/`, implementation in `m3u8_spider/`
- **Embedded Scrapy project**: Scrapy spider runs as subprocess from `scrapy_project/`
- **Recovery-oriented download**: Multi-phase download with validation and retry loops
- **Database-driven automation**: MySQL-backed task queue for daemon mode

## Layers

**CLI Layer:**
- Purpose: User-facing command entry points
- Location: `cli/`
- Contains: `main.py`, `daemon.py`, `batch_merge.py`, `m3u8_refresh_daemon.py`
- Depends on: Core modules
- Entry points: `m3u8-download`, `m3u8-daemon`, `m3u8-batch-merge`

**Core Download Layer:**
- Purpose: Download orchestration, validation, and recovery
- Location: `m3u8_spider/core/`
- Contains: `downloader.py`, `validator.py`, `recovery.py`, `m3u8_fetcher.py`
- Depends on: Config, Logger, Utils
- Coordinates: Scrapy subprocess execution

**Automation Layer:**
- Purpose: Daemon mode coordination and task scheduling
- Location: `m3u8_spider/automation/`
- Contains: `auto_downloader.py`, `m3u8_refresher.py`
- Depends on: Core, Database, Config
- Coordinates: Database queries, download tasks, cooldown timers

**Database Layer:**
- Purpose: MySQL connection and task management
- Location: `m3u8_spider/database/`
- Contains: `manager.py`
- Depends on: Logger, Config
- Used by: Automation layer

**Scrapy Engine Layer:**
- Purpose: Actual HTTP downloads of M3U8/TS segments
- Location: `scrapy_project/m3u8_spider/`
- Contains: `spiders/m3u8_downloader.py`, `pipelines.py`, `settings.py`
- Entry: `scrapy crawl m3u8_downloader`
- Runs as: Subprocess spawned by core/downloader.py

**Utils Layer:**
- Purpose: FFmpeg merge, file helpers
- Location: `m3u8_spider/utils/`
- Contains: `merger.py`, `migration.py`
- Depends on: Config, Logger

**Config/Shared Layer:**
- Purpose: Environment configuration, logging, constants
- Location: `m3u8_spider/`
- Contains: `config.py`, `logger.py`
- Used by: All layers

## Data Flow

**Manual Download Flow:**

1. `cli/main.py:main()` → Parse CLI args
2. `core/recovery.py:recover_download()` → Orchestrate flow
3. `core/downloader.py:run_scrapy()` → Spawn subprocess
4. `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py` → Parse M3U8, yield items
5. `scrapy_project/m3u8_spider/pipelines.py:M3U8FilePipeline` → Download TS files
6. Return to `recover_download()` → Validate downloads
7. If incomplete → Retry failed segments (up to 3 rounds)
8. `cli/main.py:_print_footer()` → Show completion status

**Daemon Download Flow:**

1. `cli/daemon.py:main()` → Load MySQL config, parse args
2. `automation/auto_downloader.py:AutoDownloader.run()` → Main loop
3. `database/manager.py:get_pending_tasks()` → Fetch status=0 tasks
4. For each task → `recover_download()` → Validate
5. `database/manager.py:update_task_status()` → Set status to 1 (success) or 2 (failed)
6. Sleep with cooldown → Repeat

**State Management:**
- **CLI mode**: Stateless, each run is independent
- **Daemon mode**: State persisted in MySQL (`movie_info.status`: 0=pending, 1=success, 2=failed)
- **Download state**: Metadata files in `movies/<name>/` (playlist.txt, encryption_info.json, content_lengths.json)

## Key Abstractions

**DownloadConfig:**
- Purpose: Immutable configuration for a single download
- Location: `m3u8_spider/core/downloader.py`
- Fields: `m3u8_url`, `filename`, `concurrent`, `delay`, `metadata_only`, `retry_urls`
- Provides: Path computation, URL validation

**RecoveryResult:**
- Purpose: Result of recovery process
- Location: `m3u8_spider/core/recovery.py`
- Fields: `is_complete`, `validation_result`, `retry_rounds`, `metadata_downloaded`, `retry_history`

**ValidationResult:**
- Purpose: Download validation outcome
- Location: `m3u8_spider/core/validator.py`
- Fields: `expected_count`, `actual_count`, `missing_files`, `zero_size_files`, `incomplete_files`, `failed_urls`

**DownloadTask:**
- Purpose: Database task record
- Location: `m3u8_spider/database/manager.py`
- Fields: `id`, `number`, `m3u8_address`, `status`, `title`, `provider`, `url`, `m3u8_update_time`

**M3U8Item:**
- Purpose: Scrapy item for TS segment download
- Location: `scrapy_project/m3u8_spider/items.py`
- Fields: `url`, `filename`, `directory`, `segment_index`, `file_path`, `file_status`, `file_error`

## Entry Points

**Single Download:**
- Location: `cli/main.py`
- Triggers: `m3u8-download <url> <filename>`
- Responsibilities: Parse args, run recovery, print results

**Daemon Mode:**
- Location: `cli/daemon.py`
- Triggers: `m3u8-daemon [--concurrent N] [--delay N]`
- Responsibilities: Database polling, task dispatch, status updates

**Batch Merge:**
- Location: `cli/batch_merge.py`
- Triggers: `m3u8-batch-merge [--dry-run] [--no-delete]`
- Responsibilities: Iterate movies/, validate, merge, cleanup

**Validator:**
- Location: `m3u8_spider/core/validator.py:main()`
- Triggers: `python -m m3u8_spider.core.validator <video_name>`
- Responsibilities: Check completeness, report failures

**Merger:**
- Location: `m3u8_spider/utils/merger.py:main()`
- Triggers: `python -m m3u8_spider.utils.merger <video_name> [output.mp4]`
- Responsibilities: FFmpeg concat, handle encryption

**M3U8 Refresh Daemon:**
- Location: `cli/m3u8_refresh_daemon.py`
- Triggers: `m3u8-refresh`
- Responsibilities: Update stale M3U8 URLs from source pages

## Error Handling

**Strategy:** Layered retry with validation checkpoints

**Patterns:**
1. **Scrapy subprocess**: Managed by `subprocess.run(check=True)`, errors propagate
2. **Download recovery**: 3-round retry loop for failed segments
3. **Database**: Connection retry with exponential backoff, graceful degradation
4. **Validation**: File-by-file size checking against Content-Length headers
5. **Encryption**: Key file presence check before merge

## Cross-Cutting Concerns

**Logging:** Centralized in `m3u8_spider/logger.py`
- Uses Python `logging` module
- Console + optional file output
- Level controlled via `LOG_LEVEL` env var

**Validation:** Centralized in `m3u8_spider/core/validator.py`
- `PlaylistParser` for M3U8 parsing
- `ContentLengthLoader` for expected sizes
- `DownloadValidator` for comparison

**Configuration:** Centralized in `m3u8_spider/config.py`
- `.env` file loaded on first import
- Environment variables override defaults
- MySQL config from env only

**Authentication:** N/A (no user auth)
- Encryption handled via AES-128 key files in download directory

---

*Architecture analysis: 2026-03-20*
