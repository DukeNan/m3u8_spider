# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python-based M3U8 video downloader that uses the Scrapy framework to download HLS (HTTP Live Streaming) video segments from M3U8 playlist files. The project supports two modes: **manual single downloads** via CLI and **automated batch downloads** via MySQL database integration. It uses a **recovery flow**: fill metadata → validate → retry failed TS only (up to 3 rounds). Additional utilities: `cli/batch_merge.py` (or `m3u8-batch-merge`) for batch validate/merge, `cli/sync_mp4.sh` for rsync to remote Jellyfin.

## Directory Structure

By default:
- Downloaded segments are saved to `movies/<video_name>/` at project root
- Merged MP4 files are saved to `mp4/` at project root
- Download logs are saved to `logs/<video_name>.log` at project root
- Simple names like `my_video` are resolved to `movies/my_video`
- Full paths or relative paths (like `./my_video`) are used as-is

## Commands

### Installation
```bash
source .venv/bin/activate
uv pip install -e .
```

### Download M3U8
```bash
python -m cli.main <m3u8_url> <filename> [--concurrent <num>] [--delay <seconds>]
# or: m3u8-download <m3u8_url> <filename> ...
```
- `--concurrent`: Number of concurrent downloads (default: 32)
- `--delay`: Download delay in seconds (default: 0)

### Validate Downloads
```bash
python -m m3u8_spider.core.validator <directory_or_video_name>
```
- Pass `my_video` to validate `movies/my_video`
- Pass `./my_video` to use the exact path

### Merge to MP4
```bash
python -m m3u8_spider.utils.merger <directory_or_video_name> [output.mp4]
```
- Pass `my_video` to merge from `movies/my_video` to `mp4/my_video.mp4`
- Pass custom output filename like `output.mp4` to save as `mp4/output.mp4`
- `merge_ts_files(directory, output_file, force_overwrite=True)` in `m3u8_spider.utils.merger` for programmatic use

### Batch Merge
```bash
python -m cli.batch_merge [--dry-run] [--no-delete]
# or: m3u8-batch-merge [--dry-run] [--no-delete]
```
- Iterates `movies/` subdirs: validate → merge MP4 → optionally delete source dir
- `--dry-run`: list directories only
- `--no-delete`: merge but keep source dirs

### Sync MP4 to Remote
```bash
./cli/sync_mp4.sh user@host
# or REMOTE_HOST=user@host ./cli/sync_mp4.sh
```
- Rsyncs `mp4/` to remote Jellyfin media directory

### Auto Download Daemon (MySQL Integration)
```bash
python -m cli.daemon [--concurrent <num>] [--delay <seconds>] [--check-interval <seconds>] [--cooldown <seconds>]
# or: m3u8-daemon ...
```
- Reads download tasks from MySQL database (`movie_info` table)
- Automatically downloads videos with `status=0`
- Updates status to `1` (success) or `2` (failed) after validation
- Requires `.env` file with database credentials
- Use `Ctrl+C` to gracefully stop the daemon

## Code Style

- **Path handling**: Use `pathlib.Path` instead of `os.path` for all file operations
  - `Path("a") / "b"` instead of `os.path.join("a", "b")`
  - `Path.name` instead of `os.path.basename()`
  - `Path.parent` instead of `os.path.dirname()`
  - `Path.exists()` instead of `os.path.exists()`
  - `Path.mkdir(parents=True, exist_ok=True)` instead of `os.makedirs()`
- **os module**: Only use `os.chdir()` and `os.getcwd()` where pathlib has no equivalent
- **Imports**: Add `from __future__ import annotations` for modern type hints
- **Type hints**: Use `list[str] | None` style instead of `List[str] | Optional[str]`
- **Functions over classes**: Prefer module-level functions with clear single responsibilities

## Architecture

The project is organized into three main parts: the Scrapy framework for downloading, standalone utilities for post-processing, and MySQL database integration for automated batch processing.

### Entry Points

1. **`cli/main.py`** - Primary entry point for single downloads (`python -m cli.main` or `m3u8-download`):
   - Parses CLI arguments (URL, filename, concurrency, delay)
   - Creates `DownloadConfig` and calls `m3u8_spider.core.recovery` recovery flow (not `run_scrapy()` directly)
   - Recovery flow: fill metadata → validate → retry failed TS only (max 3 rounds)

2. **`m3u8_spider/core/validator.py`** - Validation utility (`python -m m3u8_spider.core.validator`):
   - Resolves video names to `movies/<name>` for simple names
   - Reads `playlist.txt` for expected segment list
   - Compares against actual downloaded files; reports missing/empty files
   - Uses `pathlib.Path` for all file operations
   - **Can be called programmatically** by `m3u8_spider.core.recovery` and `m3u8_spider.automation.auto_downloader`

3. **`m3u8_spider/utils/merger.py`** - FFmpeg wrapper (`python -m m3u8_spider.utils.merger`):
   - Resolves video names to `movies/<name>` for simple names
   - Creates ordered file list from downloaded TS segments, uses FFmpeg to concatenate into MP4
   - Outputs to `mp4/` directory by default; `force_overwrite` for programmatic use
   - Uses `pathlib.Path` for all file operations

4. **`m3u8_spider/core/recovery.py`** - Download recovery coordinator:
   - Recovery flow: fill metadata → validate → retry failed TS only (max 3 rounds)
   - Calls `run_scrapy()` with `metadata_only=True` to fill missing playlist/encryption/key
   - Extracts `failed_urls` from validation result, builds `retry_urls` for spider
   - Returns `RecoveryResult` (is_complete, validation_result, retry_rounds, etc.)

5. **`cli/batch_merge.py`** - Batch validate/merge utility (`python -m cli.batch_merge` or `m3u8-batch-merge`):
   - Iterates `movies/` subdirs: validate → merge → optionally delete source dir
   - Uses `--dry-run` and `--no-delete` flags

6. **`cli/sync_mp4.sh`** - Rsync script to sync `mp4/` to remote Jellyfin

7. **`cli/daemon.py`** - Automated batch download daemon (`python -m cli.daemon` or `m3u8-daemon`):
   - Loads configuration via `m3u8_spider.config` (which loads `.env`; MySQL credentials, check interval, cooldown)
   - Parses CLI arguments: `--concurrent`, `--delay`, `--check-interval`, `--cooldown`
   - Creates and runs `AutoDownloader` via `create_auto_downloader()`
   - Displays real-time progress and statistics

8. **`m3u8_spider/automation/auto_downloader.py`** - Download coordinator:
   - Manages the automated download workflow
   - Fetches tasks from database via `m3u8_spider.database.manager`
   - Creates `DownloadConfig` and calls recovery flow (not `run_scrapy()` directly)
   - Recovery flow handles metadata fill + validation + retry internally
   - Updates database status based on validation results
   - Handles graceful shutdown (Ctrl+C)
   - Maintains download statistics

9. **`m3u8_spider/database/manager.py`** - Database management layer:
   - MySQL operations: get pending tasks (`status=0`), update task status, get statistics
   - Connection pooling and auto-reconnect; error handling and retry logic

10. **`m3u8_spider/core/downloader.py`** - Scrapy execution manager:
   - `DownloadConfig` dataclass: Immutable configuration (m3u8_url, filename, concurrent, delay, metadata_only, retry_urls)
   - `run_scrapy()`: Executes Scrapy via subprocess using `scrapy crawl` command
   - Passes `m3u8_url_b64` (base64-encoded) to avoid special character issues in `-a` flag
   - Uses `-a` flag for spider parameters (m3u8_url_b64, filename, download_directory, retry_urls, metadata_only)
   - Uses `-s` flag to set Scrapy settings (CONCURRENT_REQUESTS, DOWNLOAD_DELAY, M3U8_LOG_FILE)
   - Serializes `retry_urls` to JSON string when passing via command line
   - `metadata_only` and `retry_urls` cannot be used together
   - Runs command in `scrapy_project/` directory via `cwd` parameter
   - Does not capture output, allowing real-time console logging

### Scrapy Project (`scrapy_project/m3u8_spider/`)

The Scrapy project follows the standard Scrapy pattern:

- **`spiders/m3u8_downloader.py`** - Core spider with two-phase parsing:
  1. `start_requests()` → `parse_m3u8()`: Downloads and parses M3U8 playlist
  2. Yields `M3U8Item` objects for each segment (handled by pipeline)
  3. Receives `download_directory` parameter to set download location
  4. Supports `m3u8_url_b64` (base64-decoded to m3u8_url) to avoid special chars in CLI
  5. Supports `metadata_only` mode: only download playlist, encryption info, key; skip TS segments
  6. Supports `retry_urls` parameter (list[dict] or JSON string) for retry mode; resolves relative URLs in retry_urls
  7. Automatically parses JSON string `retry_urls` when passed via command line

- **`pipelines.py`** - `M3U8FilePipeline` extends Scrapy's `FilesPipeline`:
  - Overrides `file_path()` to use custom filenames
  - Uses `open_spider()` to set download directory from spider
  - Files are saved to `movies/<filename>/` by default
  - Uses `pathlib.Path` for all file operations

- **`settings.py`** - Key Scrapy configurations:
  - `CONCURRENT_REQUESTS = 32` (overrideable via CLI)
  - `AUTOTHROTTLE_ENABLED = True` for rate limiting
  - `ROBOTSTXT_OBEY = False`
  - `COOKIES_ENABLED = False`

- **`extensions.py`** - Scrapy extensions:
  - `M3U8FileLogExtension` - Configures log file output via `M3U8_LOG_FILE` setting

- **`logformatter.py`** - Custom log formatter:
  - Defines log output format for download operations

### M3U8 Parsing Strategy

The spider uses a dual parsing approach:
1. **Primary**: Uses `m3u8` library with proper URI resolution
2. **Fallback**: Manual line-by-line parsing if library fails

Both handle:
- Absolute URLs (http://...)
- Root-relative URLs (/path/...)
- Path-relative URLs (segment.ts or ../segment.ts)

## Data Flow

### Manual Single Download Mode (with Recovery Flow)

1. User runs `python -m cli.main` (or `m3u8-download`) with M3U8 URL and filename
2. `cli/main.py` parses arguments and creates `DownloadConfig`
3. Calls `m3u8_spider.core.recovery` recovery flow (max 3 retry rounds)
4. Recovery flow:
   - Checks for missing metadata (playlist.txt, encryption_info.json, encryption.key, content_lengths.json)
   - If missing: calls `run_scrapy(config with metadata_only=True)` to fill only metadata
   - Runs `validate_downloads()` to verify completeness
   - If incomplete: extracts `failed_urls`, builds `retry_urls`, calls `run_scrapy(config with retry_urls)`
   - Repeats retry up to 3 rounds until complete or max reached
5. `run_scrapy()` creates download directory under `movies/<filename>/`, log directory under `logs/`
6. Spider receives `m3u8_url_b64` (base64), `metadata_only`, or `retry_urls` via `-a` flags
7. Spider downloads M3U8 file / metadata / or retry TS files only
8. Pipeline downloads each TS file to specified directory
9. Logs written to console and `logs/<filename>.log`
10. User runs `python -m m3u8_spider.utils.merger` to create MP4 in `mp4/` directory

### Automated Batch Download Mode (MySQL Integration)

1. User configures database credentials in `.env` file
2. User starts daemon: `python -m cli.daemon` or `m3u8-daemon`
3. `cli/daemon.py` loads config and creates `AutoDownloader` via `create_auto_downloader()`
4. `AutoDownloader` connects to MySQL database via `m3u8_spider.database.manager`
5. Main loop begins:
   - Query `movie_info` table for records with `status=0`
   - For each task:
     - Extract `number` (used as filename) and `m3u8_address`
     - Create `DownloadConfig` with task data
     - Call `m3u8_spider.core.recovery` recovery flow (metadata + validation + retry, max 3 rounds)
     - Each download runs in independent subprocess, avoiding reactor conflicts
     - Update database: `status=1` (success) or `status=2` (failed)
     - Update `m3u8_update_time` timestamp
   - Sleep for configured interval
   - Repeat until interrupted (Ctrl+C)
6. On shutdown: close database connection, print statistics, exit gracefully

## Important Notes

### General
- **Unified config**: `m3u8_spider/config.py` loads `.env` and defines all constants (defaults and env-overridable). Use `from m3u8_spider.config import ...` for constants; use `get_mysql_config()` for daemon DB credentials. See `config.py` docstring for env var names.
- Default download directory is `movies/` at project root
- Default log directory is `logs/` at project root
- Default MP4 output directory is `mp4/` at project root
- Scrapy is executed via subprocess using `scrapy crawl` command
- The subprocess runs in `scrapy_project/` directory (via `cwd` parameter)
- `download_directory` is passed to spider via `-a` command line flag
- The `_resolve_directory()` helper resolves simple names to `movies/<name>`
- Scrapy's `M3U8_LOG_FILE` setting configures the log file path (via `-s` flag)
- When modifying the spider, remember that `download_directory` is an absolute path
- The `m3u8` library requires the base M3U8 URI for proper relative URL resolution
- Use `pathlib.Path` for all file operations
- `retry_urls` parameter is serialized to JSON string when passed via command line
- Spider automatically parses JSON string `retry_urls` back to list[dict]
- `m3u8_url` is passed via `m3u8_url_b64` (base64-encoded) to avoid special character issues in CLI
- `metadata_only` and `retry_urls` cannot be used together in `DownloadConfig`

### MySQL Integration
- Configuration is loaded from `.env` file (not tracked in git); `config.py` loads it on first import.
- Use `env.example` as template for creating `.env`; full option list in `config.py`.
- Database table `movie_info` must have these fields:
  - `id`: Primary key
  - `number`: Video identifier (used as filename)
  - `m3u8_address`: M3U8 URL to download
  - `status`: Download status (0=pending, 1=success, 2=failed)
  - `m3u8_update_time`: Timestamp of last update
- The daemon uses `number` field as the download directory name
- Downloads are saved to `movies/<number>/`
- Logs are saved to `logs/<number>.log`
- The daemon continues running until manually stopped (Ctrl+C)
- Failed tasks (status=2) can be reset to 0 for retry
- The `m3u8_spider.automation.auto_downloader` module uses the recovery flow in `m3u8_spider.core.recovery`, which internally uses `run_scrapy()` and `m3u8_spider.core.validator.validate_downloads()`
- Each download runs in an independent subprocess, preventing reactor conflicts in batch processing

### Dependencies
- Core: `scrapy`, `m3u8`, `requests`
- MySQL integration: `pymysql`, `python-dotenv`
- Optional: `ffmpeg` (for merging to MP4)

### Documentation
- `README.md`: General usage guide
- `QUICKSTART.md`: 5-minute quick start for MySQL integration
- `AUTO_DOWNLOAD_README.md`: Complete MySQL integration manual (500+ lines)
- `TESTING.md`: Testing and validation guide (400+ lines)
- `IMPLEMENTATION_SUMMARY.md`: Technical implementation details
