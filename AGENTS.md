# Repository Guidelines

## Project Structure & Module Organization

- `m3u8_spider/core/` contains download, validation, recovery, and page-to-M3U8 fetching logic.
- `m3u8_spider/automation/` contains long-running database-backed download and refresh daemons.
- `m3u8_spider/database/` owns MySQL access and task status updates; keep SQL out of CLI and core modules.
- `scrapy_project/` is the Scrapy project and its downloader spider, pipelines, and settings.
- `cli/` provides command entry points. `tests/` mirrors source areas (`tests/core/`, `tests/scrapy/`).
- Runtime output belongs in `movies/`, `mp4/`, and `logs/`; do not commit generated media or credentials.

## Build, Test, and Development Commands

Use Python 3.14+ and `uv`.

```bash
uv pip install -e ".[dev]"             # install the project and test/lint tools
make test                              # run the full pytest suite
make test-cov                          # run tests with terminal coverage output
make lint                              # run Ruff checks
make format                            # format with Ruff
uv run m3u8-download <url> <name>      # download one playlist
uv run m3u8-daemon                     # run the MySQL download daemon
uv run m3u8-refresh                    # refresh M3U8 URLs from page URLs
```

Install the optional page crawler before using refresh: `uv pip install -e ".[crawl]"`; Playwright browser setup may also be required by crawl4ai.

## Coding Style & Naming Conventions

Use four-space indentation, type annotations, and `from __future__ import annotations` in new Python modules. Ruff targets Python 3.14 with a 100-character line limit; run `make format` and `make lint` before review. Use `snake_case` for functions/modules, `PascalCase` for classes, and `test_<behavior>.py` or `test_<behavior>` for tests. Keep responsibilities local: database operations in `DatabaseManager`, Scrapy behavior in `scrapy_project`, and orchestration in `automation`.

## Testing Guidelines

Use `pytest`; tests are discovered under `tests/` from files named `test_*.py`. Add a focused regression test for every bug fix, especially parser, URL-resolution, recovery, or status-transition changes. Mock network, crawler, and database boundaries so unit tests stay offline:

```bash
uv run pytest tests/core/test_m3u8_fetcher.py
```

## Commits, Pull Requests, and Configuration

Existing history uses Conventional Commit-style subjects such as `feat:`, `fix:`, `test:`, `refactor:`, and `chore:`. Keep commits small and imperative. PRs should state the behavioral change, testing run, and any schema/configuration effect; include logs or screenshots only when they clarify CLI behavior.

Copy `env.example` to `.env` for MySQL settings. Never commit `.env`, database passwords, access tokens, or real media URLs containing credentials.
