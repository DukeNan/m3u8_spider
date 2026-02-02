# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Python-based M3U8 video downloader that uses the Scrapy framework to download HLS (HTTP Live Streaming) video segments from M3U8 playlist files. The project follows a three-phase workflow: download, validate, and merge.

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
python validate_downloads.py <directory>
```

### Merge to MP4
```bash
python merge_to_mp4.py <directory> [output.mp4]
```

## Architecture

The project is organized into two main parts: the Scrapy framework for downloading and standalone utilities for post-processing.

### Entry Points

1. **`main.py`** - Primary entry point that:
   - Parses CLI arguments (URL, filename, concurrency, delay)
   - Configures Scrapy settings (changes working directory to `scrapy_project/`)
   - Spawns the `M3U8DownloaderSpider`

2. **`validate_downloads.py`** - Validation utility that:
   - Reads `playlist.txt` for expected segment list
   - Compares against actual downloaded files
   - Reports missing/empty files

3. **`merge_to_mp4.py`** - FFmpeg wrapper that:
   - Creates ordered file list from downloaded TS segments
   - Uses FFmpeg to concatenate into MP4

### Scrapy Project (`scrapy_project/`)

The Scrapy project follows the standard Scrapy pattern:

- **`spiders/m3u8_downloader.py`** - Core spider with two-phase parsing:
  1. `start_requests()` → `parse_m3u8()`: Downloads and parses the M3U8 playlist
  2. Yields `M3U8Item` objects for each segment (handled by pipeline)

- **`pipelines.py`** - `M3U8FilePipeline` extends Scrapy's `FilesPipeline`:
  - Overrides `file_path()` to use custom filenames
  - Uses `open_spider()` to set the download directory from the spider
  - Files are saved to a directory named after the `<filename>` argument

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
2. `main.py` changes to `scrapy_project/` directory and runs the spider
3. Spider downloads the M3U8 file and saves it as `<filename>/playlist.txt`
4. Spider yields items for each TS segment URL
5. Pipeline downloads each TS file to `<filename>/` directory
6. User runs validation script to verify completeness
7. User runs merge script to create MP4

## Important Notes

- The working directory is changed to `scrapy_project/` during download operation
- Download directory is created at the project root (one level up from `scrapy_project/`)
- When modifying the spider, remember that `download_directory` is set relative to the spider's working directory
- The `m3u8` library requires the base M3U8 URI for proper relative URL resolution
