# Codebase Structure

**Analysis Date:** 2026-03-20

## Directory Layout

```
m3u8_spider/
├── .planning/              # GSD planning documents (DO NOT commit to git)
├── .venv/                  # Python virtual environment
├── .env                    # Environment variables (contains secrets)
├── cli/                    # CLI entry points
├── m3u8_spider/            # Main package
│   ├── automation/          # Daemon coordination
│   ├── core/               # Download engine
│   ├── database/           # MySQL operations
│   └── utils/              # FFmpeg, helpers
├── scrapy_project/         # Embedded Scrapy project
│   └── m3u8_spider/        # Scrapy spider code
├── movies/                 # Downloaded TS segments
├── mp4/                    # Merged MP4 files
├── logs/                   # Download logs
└── pyproject.toml          # Package definition
```

## Directory Purposes

**`cli/`:**
- Purpose: User-facing command-line interfaces
- Contains: `main.py` (single download), `daemon.py` (auto download), `batch_merge.py`, `m3u8_refresh_daemon.py`, `__init__.py`
- Key files: Entry points registered in `pyproject.toml`

**`m3u8_spider/`:**
- Purpose: Core library package
- Contains: `__init__.py`, `config.py`, `logger.py`, subdirectories

**`m3u8_spider/core/`:**
- Purpose: Download orchestration and validation
- Contains: `downloader.py`, `validator.py`, `recovery.py`, `m3u8_fetcher.py`, `__init__.py`
- Key abstractions: `DownloadConfig`, `RecoveryResult`, `ValidationResult`

**`m3u8_spider/automation/`:**
- Purpose: Daemon mode coordination
- Contains: `auto_downloader.py`, `m3u8_refresher.py`, `__init__.py`
- Coordinates: Database queries, recovery flow, cooldown timers

**`m3u8_spider/database/`:**
- Purpose: MySQL database operations
- Contains: `manager.py`, `__init__.py`
- Key abstractions: `DatabaseManager`, `DownloadTask`

**`m3u8_spider/utils/`:**
- Purpose: FFmpeg merge and migration utilities
- Contains: `merger.py`, `migration.py`, `__init__.py`

**`scrapy_project/`:**
- Purpose: Embedded Scrapy project
- Contains: `__init__.py`, `m3u8_spider/` subpackage

**`scrapy_project/m3u8_spider/`:**
- Purpose: Scrapy spider implementation
- Contains: `spiders/`, `pipelines.py`, `settings.py`, `items.py`, `middlewares.py`, `extensions.py`, `logformatter.py`

**`movies/`:**
- Purpose: Downloaded TS segments (generated)
- Structure: `movies/<video_name>/segment_00001.ts`, `playlist.txt`, `encryption_info.json`, `content_lengths.json`

**`mp4/`:**
- Purpose: Merged video files (generated)
- Structure: `mp4/<video_name>.mp4`

**`logs/`:**
- Purpose: Download logs (generated)
- Structure: `logs/<video_name>.log`

## Key File Locations

**Entry Points:**
- `cli/main.py`: Single video download (`m3u8-download`)
- `cli/daemon.py`: Auto download daemon (`m3u8-daemon`)
- `cli/batch_merge.py`: Batch merge TS to MP4 (`m3u8-batch-merge`)
- `cli/m3u8_refresh_daemon.py`: M3U8 URL refresher (`m3u8-refresh`)

**Configuration:**
- `m3u8_spider/config.py`: All config constants and env loading
- `.env`: Runtime secrets (never commit)
- `env.example`: Template for `.env`
- `scrapy_project/m3u8_spider/settings.py`: Scrapy settings

**Core Logic:**
- `m3u8_spider/core/downloader.py`: `DownloadConfig`, `run_scrapy()`
- `m3u8_spider/core/recovery.py`: `recover_download()`, recovery orchestration
- `m3u8_spider/core/validator.py`: `DownloadValidator`, validation logic
- `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`: `M3U8DownloaderSpider`
- `scrapy_project/m3u8_spider/pipelines.py`: `M3U8FilePipeline`

**Automation:**
- `m3u8_spider/automation/auto_downloader.py`: `AutoDownloader`, daemon loop
- `m3u8_spider/database/manager.py`: `DatabaseManager`, MySQL operations

**Utilities:**
- `m3u8_spider/utils/merger.py`: `MP4Merger`, FFmpeg integration
- `m3u8_spider/logger.py`: `setup_logger()`, `get_logger()`

**Testing:**
- Not detected (no test directory or test files found)

## Naming Conventions

**Files:**
- Python modules: `lowercase_with_underscores.py` (e.g., `downloader.py`, `merger.py`)
- Scrapy spider: `lowercase_with_underscores.py` (e.g., `m3u8_downloader.py`)
- Data classes: Same as modules

**Directories:**
- Python packages: `lowercase_with_underscores/` (e.g., `m3u8_spider/`, `core/`)
- Scrapy project: `lowercase_with_underscores/` (e.g., `scrapy_project/`)

**Functions:**
- Module-level: `lowercase_with_underscores()` (e.g., `run_scrapy()`, `recover_download()`)
- Classes: `PascalCase` (e.g., `DownloadConfig`, `AutoDownloader`)
- Dataclass fields: `snake_case` (PEP 8 style)
- Private methods: `_leading_underscore()`

**Variables:**
- Snake case: `download_config`, `failed_files`
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONCURRENT`, `LOGS_DIR`)

**Types:**
- Class-based: `DownloadConfig`, `ValidationResult`
- Type hints: `list[str]`, `dict[str, int]`, `Path`, `Optional[str]`

## Where to Add New Code

**New CLI Command:**
- Create: `cli/<command_name>.py`
- Register entry point in `pyproject.toml` under `[project.scripts]`
- Follow pattern of `cli/main.py` for argument parsing

**New Core Module:**
- Create: `m3u8_spider/core/<module_name>.py`
- Import shared dependencies from `config.py`, `logger.py`
- Export main class/function in `m3u8_spider/core/__init__.py` if needed

**New Automation Component:**
- Create: `m3u8_spider/automation/<component>.py`
- Coordinate with `database/manager.py` for task persistence
- Register CLI entry point if daemon mode

**New Scrapy Extension/Middleware:**
- Create: `scrapy_project/m3u8_spider/<component>.py`
- Register in `scrapy_project/m3u8_spider/settings.py`
- Follow Scrapy extension API

**Utilities/Helpers:**
- Shared: `m3u8_spider/utils/<helper>.py`
- Constants: Add to `m3u8_spider/config.py`

## Special Directories

**`scrapy_project/`:**
- Purpose: Embedded Scrapy project (must run from this directory)
- Generated: No
- Committed: Yes (part of source)
- Note: Scrapy requires specific directory structure; this is intentional

**`movies/`:**
- Purpose: Downloaded video segments
- Generated: Yes (by downloader)
- Committed: No (.gitignore)
- Note: Contains `playlist.txt`, `encryption_info.json`, `content_lengths.json`

**`mp4/`:**
- Purpose: Merged video output
- Generated: Yes (by merger)
- Committed: No (.gitignore)

**`logs/`:**
- Purpose: Per-video download logs
- Generated: Yes (by M3U8FileLogExtension)
- Committed: No (.gitignore)

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by `uv venv`)
- Committed: No (.gitignore)

**`.planning/`:**
- Purpose: GSD planning documents
- Generated: Yes (by GSD commands)
- Committed: Per project decision (usually yes for reference)

---

*Structure analysis: 2026-03-20*
