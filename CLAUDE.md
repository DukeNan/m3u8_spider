# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python-based M3U8 video downloader that uses the Scrapy framework to download HLS (HTTP Live Streaming) video segments from M3U8 playlist files. The project supports two modes: **manual single downloads** via CLI and **automated batch downloads** via MySQL database integration. It follows a three-phase workflow: download, validate, and merge.

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
python main.py <m3u8_url> <filename> [--concurrent <num>] [--delay <seconds>]
```
- `--concurrent`: Number of concurrent downloads (default: 32)
- `--delay`: Download delay in seconds (default: 0)

### Validate Downloads
```bash
python validate_downloads.py <directory_or_video_name>
```
- Pass `my_video` to validate `movies/my_video`
- Pass `./my_video` to use the exact path

### Merge to MP4
```bash
python merge_to_mp4.py <directory_or_video_name> [output.mp4]
```
- Pass `my_video` to merge from `movies/my_video` to `mp4/my_video.mp4`
- Pass custom output filename like `output.mp4` to save as `mp4/output.mp4`

### Auto Download Daemon (MySQL Integration)
```bash
python auto_download_daemon.py [--concurrent <num>] [--delay <seconds>] [--check-interval <seconds>]
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

1. **`main.py`** - Primary entry point for single downloads:
   - Parses CLI arguments (URL, filename, concurrency, delay)
   - Creates `DownloadConfig` and calls `scrapy_manager.run_scrapy()`
   - Uses function-based architecture: `_parse_args()`, `_print_header()`, `_print_footer()`
   - **Can be called programmatically** by `auto_downloader.py` for batch processing

2. **`validate_downloads.py`** - Validation utility:
   - Uses `_resolve_directory()` helper to resolve video names to `movies/<name>`
   - Reads `playlist.txt` for expected segment list
   - Compares against actual downloaded files
   - Reports missing/empty files
   - Uses `pathlib.Path` for all file operations
   - **Can be called programmatically** by `auto_downloader.py`

3. **`merge_to_mp4.py`** - FFmpeg wrapper:
   - Uses `_resolve_directory()` helper to resolve video names to `movies/<name>`
   - Creates ordered file list from downloaded TS segments
   - Uses FFmpeg to concatenate into MP4
   - Outputs to `mp4/` directory by default
   - Uses `pathlib.Path` for all file operations

4. **`auto_download_daemon.py`** - Automated batch download daemon:
   - Loads configuration from `.env` file (MySQL credentials, check interval)
   - Parses CLI arguments for overriding defaults
   - Creates and runs `AutoDownloader` instance
   - Displays real-time progress and statistics

5. **`auto_downloader.py`** - Download coordinator:
   - Manages the automated download workflow
   - Fetches tasks from database via `db_manager.py`
   - Creates `DownloadConfig` and calls `scrapy_manager.run_scrapy()` for downloading
   - Calls `validate_downloads.validate_downloads()` for validation
   - Updates database status based on validation results
   - Handles graceful shutdown (Ctrl+C)
   - Maintains download statistics

6. **`db_manager.py`** - Database management layer:
   - `DatabaseManager` class for MySQL operations
   - `get_pending_tasks()`: Query tasks with `status=0`
   - `update_task_status()`: Update task status and timestamp
   - `get_statistics()`: Get download statistics
   - Connection pooling and auto-reconnect
   - Error handling and retry logic

7. **`scrapy_manager.py`** - Scrapy execution manager:
   - `DownloadConfig` dataclass: Immutable configuration for downloads
   - `run_scrapy()`: Executes Scrapy via subprocess using `scrapy crawl` command
   - Uses `-a` flag to pass spider parameters (m3u8_url, filename, download_directory, retry_urls)
   - Uses `-s` flag to set Scrapy settings (CONCURRENT_REQUESTS, DOWNLOAD_DELAY, M3U8_LOG_FILE)
   - Serializes `retry_urls` to JSON string when passing via command line
   - Runs command in `scrapy_project/` directory via `cwd` parameter
   - Does not capture output, allowing real-time console logging

### Scrapy Project (`scrapy_project/`)

The Scrapy project follows the standard Scrapy pattern:

- **`spiders/m3u8_downloader.py`** - Core spider with two-phase parsing:
  1. `start_requests()` → `parse_m3u8()`: Downloads and parses M3U8 playlist
  2. Yields `M3U8Item` objects for each segment (handled by pipeline)
  3. Receives `download_directory` parameter to set download location
  4. Supports `retry_urls` parameter (list[dict] or JSON string) for retry mode
  5. Automatically parses JSON string `retry_urls` when passed via command line

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

### Manual Single Download Mode

1. User runs `main.py` with M3U8 URL and filename
2. `main.py` parses arguments and creates `DownloadConfig`
3. `main.py` calls `scrapy_manager.run_scrapy(config)`
4. `run_scrapy()` creates download directory under `movies/<filename>/`
5. `run_scrapy()` creates log directory under `logs/`
6. `run_scrapy()` builds `scrapy crawl` command with `-a` and `-s` flags
7. `run_scrapy()` executes subprocess in `scrapy_project/` directory (via `cwd`)
8. Spider receives parameters via command line (`-a` flags)
9. Spider downloads M3U8 file and saves it as `<directory>/playlist.txt`
10. Spider yields items for each TS segment URL
11. Pipeline downloads each TS file to specified directory
12. Logs are written to both console (real-time) and `logs/<filename>.log` (via M3U8FileLogExtension)
13. User runs validation script to verify completeness
14. User runs merge script to create MP4 in `mp4/` directory

### Automated Batch Download Mode (MySQL Integration)

1. User configures database credentials in `.env` file
2. User starts daemon: `python auto_download_daemon.py`
3. `auto_download_daemon.py` loads config and creates `AutoDownloader`
4. `AutoDownloader` connects to MySQL database via `DatabaseManager`
5. Main loop begins:
   - Query `movie_info` table for records with `status=0`
   - For each task:
     - Extract `number` (used as filename) and `m3u8_address`
     - Create `DownloadConfig` with task data
     - Call `scrapy_manager.run_scrapy(config)` to download (uses subprocess)
     - Each download runs in independent subprocess, avoiding reactor conflicts
     - Call `validate_downloads()` to verify
     - Update database: `status=1` (success) or `status=2` (failed)
     - Update `m3u8_update_time` timestamp
   - Sleep for configured interval
   - Repeat until interrupted (Ctrl+C)
6. On shutdown: close database connection, print statistics, exit gracefully

## Important Notes

### General
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

### MySQL Integration
- Configuration is loaded from `.env` file (not tracked in git)
- Use `env.example` as template for creating `.env`
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
- The `auto_downloader.py` module calls `scrapy_manager.run_scrapy()` and `validate_downloads()` functions
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
