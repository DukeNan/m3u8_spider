# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python-based M3U8 video downloader that uses the Scrapy framework to download HLS (HTTP Live Streaming) video segments from M3U8 playlist files. The project follows a three-phase workflow: download, validate, and merge.

## Directory Structure

By default:
- Downloaded segments are saved to `movies/<video_name>/` at project root
- Merged MP4 files are saved to `mp4/` at project root
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

## Architecture

The project is organized into two main parts: the Scrapy framework for downloading and standalone utilities for post-processing.

### Entry Points

1. **`main.py`** - Primary entry point that:
   - Parses CLI arguments (URL, filename, concurrency, delay)
   - Configures Scrapy settings (changes working directory to `scrapy_project/`)
   - Spawns the `M3U8DownloaderSpider` with `download_directory` parameter
   - Uses `DownloadConfig` dataclass for immutable configuration
   - Creates download directories under `movies/` by default

2. **`validate_downloads.py`** - Validation utility that:
   - Uses `_resolve_directory()` helper to resolve video names to `movies/<name>`
   - Reads `playlist.txt` for expected segment list
   - Compares against actual downloaded files
   - Reports missing/empty files
   - Uses `pathlib.Path` for all file operations

3. **`merge_to_mp4.py`** - FFmpeg wrapper that:
   - Uses `_resolve_directory()` helper to resolve video names to `movies/<name>`
   - Creates ordered file list from downloaded TS segments
   - Uses FFmpeg to concatenate into MP4
   - Outputs to `mp4/` directory by default
   - Uses `pathlib.Path` for all file operations

### Scrapy Project (`scrapy_project/`)

The Scrapy project follows the standard Scrapy pattern:

- **`spiders/m3u8_downloader.py`** - Core spider with two-phase parsing:
  1. `start_requests()` → `parse_m3u8()`: Downloads and parses M3U8 playlist
  2. Yields `M3U8Item` objects for each segment (handled by pipeline)
  3. Receives `download_directory` parameter to set the download location

- **`pipelines.py`** - `M3U8FilePipeline` extends Scrapy's `FilesPipeline`:
  - Overrides `file_path()` to use custom filenames
  - Uses `open_spider()` to set the download directory from the spider
  - Files are saved to `movies/<filename>/` by default
  - Uses `pathlib.Path` for all file operations

- **`settings.py`** - Key Scrapy configurations:
  - `CONCURRENT_REQUESTS = 32` (overrideable via CLI)
  - `AUTOTHROTTLE_ENABLED = True` for rate limiting
  - `ROBOTSTXT_OBEY = False`
  - `COOKIES_ENABLED = False`

### M3U8 Parsing Strategy

The spider uses a dual parsing approach:
1. **Primary**: Uses `m3u8` library with proper URI resolution
2. **Fallback**: Manual line-by-line parsing if library fails

Both handle:
- Absolute URLs (http://...)
- Root-relative URLs (/path/...)
- Path-relative URLs (segment.ts or ../segment.ts)

## Data Flow

1. User runs `main.py` with M3U8 URL and filename
2. `main.py` creates download directory under `movies/<filename>/`
3. `main.py` changes to `scrapy_project/` directory and runs the spider
4. Spider receives `download_directory` as parameter
5. Spider downloads the M3U8 file and saves it as `<directory>/playlist.txt`
6. Spider yields items for each TS segment URL
7. Pipeline downloads each TS file to the specified directory
8. User runs validation script to verify completeness
9. User runs merge script to create MP4 in `mp4/` directory

## Important Notes

- Default download directory is `movies/` at project root
- Default MP4 output directory is `mp4/` at project root
- The working directory is changed to `scrapy_project/` during download operation
- `download_directory` is passed directly to the spider as a parameter
- The `_resolve_directory()` helper resolves simple names to `movies/<name>`
- When modifying the spider, remember that `download_directory` is an absolute path
- The `m3u8` library requires the base M3U8 URI for proper relative URL resolution
- Use `pathlib.Path` for all file operations, only use `os` for `chdir()` and `getcwd()`
