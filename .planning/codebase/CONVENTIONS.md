# Coding Conventions

**Analysis Date:** 2026-03-29

## Style Configuration

**Tool:** ruff (v0.15.0+)
**Config:** `pyproject.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
```

**Key Rules:**
- E/F/W: Pyflakes/pycodestyle errors/warnings
- I: Import sorting (isort rules)
- UP: Python 3.x upgrade rules
- B: Flake8 bugbear rules

## Naming Patterns

**Files:**
- Python modules: `snake_case.py`
- CLI entry points: `cli/main.py`, `cli/daemon.py`
- Package modules: `m3u8_spider/core/downloader.py`
- Test files: `test_*.py` or `*_test.py` (not currently used)

**Classes:**
- PascalCase for data classes and service classes
- Examples: `DownloadConfig`, `DatabaseManager`, `AutoDownloader`, `MP4Merger`, `DownloadValidator`
- Data classes for configuration/results: `DownloadTask`, `RecoveryResult`, `ValidationResult`

**Functions/Methods:**
- snake_case for all functions and methods
- Private helpers prefixed with `_`: `_parse_args()`, `_ensure_connection()`, `_yield_retry_items()`
- Module-level functions preferred over classes per CLAUDE.md: `recover_download()`, `validate_downloads()`, `merge_ts_files()`, `run_scrapy()`

**Variables:**
- snake_case for all variables
- Examples: `download_dir`, `m3u8_url`, `retry_rounds`, `failed_urls`

**Constants:**
- UPPER_SNAKE_CASE at module level
- Examples: `DEFAULT_CONCURRENT`, `INVALID_FILENAME_CHARS`, `CONTENT_LENGTHS_FILE`, `LOGS_DIR`

**Type Variables:**
- PascalCase in generic contexts
- Union syntax: `list[str] | None` (Python 3.10+ style)

## File Header Pattern

**All Python files follow this header pattern:**

```python
#!/usr/bin/env python3
"""
模块描述
具体职责说明
"""

from __future__ import annotations

import standard_library
import third_party
from local_package import ...
```

- Shebang line `#!/usr/bin/env python3` for executable scripts
- Docstring describes module purpose and responsibilities
- `from __future__ import annotations` is mandatory after docstring
- Imports follow standard → third-party → local ordering

## Required Imports

**Always include:**
```python
from __future__ import annotations
```

**Why:**
- Enables forward references without string quoting
- Allows modern type union syntax (`str | None` instead of `Optional[str]`)
- Required by ruff UP rules for Python 3.10+ compatibility

**Location:** After module docstring, before all other imports

## Import Organization

**Order (enforced by ruff I001):**
1. `from __future__ import annotations`
2. Standard library imports (`import json`, `import sys`, `from pathlib import Path`)
3. Third-party imports (`import scrapy`, `import pymysql`, `from tqdm import tqdm`)
4. Local imports (`from m3u8_spider.config import ...`)

**Multi-line imports:**
```python
from m3u8_spider.config import (
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    DOWNLOAD_COOLDOWN_SECONDS,
    get_mysql_config,
)
```

**Common import patterns by module type:**

CLI entry (`cli/main.py`):
```python
from __future__ import annotations
import argparse
import sys
from m3u8_spider.config import DEFAULT_BASE_DIR, DEFAULT_CONCURRENT, DEFAULT_DELAY, LOGS_DIR
from m3u8_spider.logger import get_logger
from m3u8_spider.core.recovery import recover_download
from m3u8_spider.core.downloader import DownloadConfig
```

Core module (`m3u8_spider/core/downloader.py`):
```python
from __future__ import annotations
import subprocess
import sys
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from pathlib import Path
from m3u8_spider.config import DEFAULT_BASE_DIR, DEFAULT_CONCURRENT, DEFAULT_DELAY, ...
from m3u8_spider.logger import get_logger
```

## Type Hints

**Union Syntax (Python 3.10+):**
```python
# Prefer this style over Optional[str]
def func(x: str | None) -> list[dict] | None:
    pass

# Not: Optional[str], Union[str, None]
```

**Generic Collections:**
```python
# Use lowercase generics (Python 3.9+)
def get_items() -> list[str]:
    return []

def get_mapping() -> dict[str, int]:
    return {}

# Not: List[str], Dict[str, int]
```

**Dataclass Types:**
```python
@dataclass(frozen=True)
class DownloadConfig:
    m3u8_url: str
    filename: str
    concurrent: int = DEFAULT_CONCURRENT
    delay: float = DEFAULT_DELAY
    metadata_only: bool = False
    retry_urls: list[dict] | None = None  # Union with None
```

**Method Return Types:**
```python
def validate(self) -> ValidationResult | None:
    """返回校验结果，目录无效时返回 None"""
    ...

def _ensure_connection(self) -> bool:
    """返回连接是否可用"""
    ...
```

**Property Types:**
```python
@property
def sanitized_filename(self) -> str:
    """清理后的文件名"""
    return self.filename.strip()

@property
def failed_files(self) -> list[str]:
    """所有失败文件列表"""
    return sorted(set(self.missing_files) | set(self.zero_size_files))
```

**Callable Types:**
```python
# Signal handler
def _signal_handler(self, signum, frame) -> None:
    ...
```

## Dataclass Usage

**Immutable Configuration (frozen=True):**
```python
@dataclass(frozen=True)
class DownloadConfig:
    """M3U8 下载配置（不可变）"""

    m3u8_url: str
    filename: str

    def __post_init__(self) -> None:
        if not self.m3u8_url.startswith(("http://", "https://")):
            raise ValueError(f"无效的URL: {self.m3u8_url}")
```

**Mutable Result/Stats:**
```python
@dataclass
class RecoveryResult:
    is_complete: bool
    validation_result: dict
    retry_rounds: int
    metadata_downloaded: bool
    retry_history: list[int] = field(default_factory=list)


@dataclass
class DownloadStats:
    total_processed: int = 0
    success_count: int = 0
    failed_count: int = 0

    def record_success(self) -> None:
        self.total_processed += 1
        self.success_count += 1
```

**Default values:**
```python
# Use field(default_factory=list) for mutable defaults
retry_history: list[int] = field(default_factory=list)

# Direct assignment for immutable defaults
concurrent: int = DEFAULT_CONCURRENT
```

## Path Handling

**Always use pathlib.Path:**

```python
from pathlib import Path

# Construction
download_dir = project_root / DEFAULT_BASE_DIR / self.sanitized_filename

# Directory creation
download_dir.mkdir(parents=True, exist_ok=True)

# File reading
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

# File writing
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Path resolution
project_root = Path(__file__).resolve().parent.parent.parent

# Check existence
if not path.exists():
    ...

# Iterate directory
for p in Path(directory).iterdir():
    if p.suffix == ".ts" and p.is_file():
        files.append(p.name)
```

**Never use os.path:**
```python
# Bad
import os
path = os.path.join(base, name)

# Good
from pathlib import Path
path = Path(base) / name
```

## Logging

**Initialization Pattern:**
```python
from m3u8_spider.logger import get_logger

logger = get_logger(__name__)  # Always use __name__
```

**Log Format (configured in config.py):**
```python
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
```

**Log Levels:**
```python
logger.info(f"下载目录: {download_dir}")
logger.info(f"✅ 校验通过: 所有文件已完整下载")
logger.warning(f"⚠️  检测到缺失文件: {filename}")
logger.error(f"❌ 下载失败: {e}")
```

**Emoji conventions:**
- Success: `✅`
- Warning: `⚠️`
- Error: `❌`
- Info: `📊`, `📥`, `🚀`, `🧹`, `👋`
- Progress: `⏳`, `⏱️`

## Error Handling

**Validation with ValueError:**
```python
def __post_init__(self) -> None:
    if not self.m3u8_url.startswith(("http://", "https://")):
        raise ValueError(f"无效的URL: {self.m3u8_url}")
    if not self.filename or not self.filename.strip():
        raise ValueError("文件名不能为空")
    if self.metadata_only and self.retry_urls:
        raise ValueError("metadata_only 与 retry_urls 不能同时启用")
```

**Graceful Degradation:**
```python
# Return default value instead of raising
try:
    data = json.load(f)
    return data if isinstance(data, dict) else {}
except Exception:
    return {}

# Return empty list on failure
try:
    cursor.execute(sql, (limit,))
    return [DownloadTask(...) for row in cursor.fetchall()]
except pymysql.Error as e:
    logger.error(f"❌ 查询失败: {e}")
    return []
```

**Boolean success/failure pattern:**
```python
def update_task_status(self, task_id: int, status: int) -> bool:
    """更新成功返回 True，失败返回 False"""
    try:
        cursor.execute(sql, (status, task_id))
        return cursor.rowcount > 0
    except pymysql.Error as e:
        logger.error(f"❌ 更新失败: {e}")
        return False
```

**Subprocess error handling:**
```python
subprocess.run(cmd, cwd=str(scrapy_project_dir), check=True, capture_output=False)
# check=True raises CalledProcessError on failure
```

## Docstrings

**Module Docstring:**
```python
"""
统一配置文件
合并原 constants.py 与 env.example 的配置项。
首次导入时加载项目根目录下的 .env 文件，环境变量可覆盖下方可覆盖项。
"""
```

**Class Docstring:**
```python
class DatabaseManager:
    """MySQL 数据库管理器，负责连接池和所有数据库操作"""


class DownloadValidator:
    """
    校验下载目录：解析 playlist、统计 ts 文件、对比 Content-Length，
    输出 ValidationResult 并可选打印报告。
    """
```

**Function Docstring:**
```python
def recover_download(config: DownloadConfig, max_retry_rounds: int = 3) -> RecoveryResult:
    """
    执行下载恢复流程：
    - 补齐关键文件
    - 校验
    - 仅重下失败 TS（最多 max_retry_rounds 轮）
    """


def get_mysql_config() -> dict[str, str | int]:
    """
    从环境变量读取 MySQL 配置并校验必需项。

    Returns:
        包含 MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE 的字典。
        MYSQL_PORT 已转为 int。

    Raises:
        ValueError: 缺少任一必需的环境变量时。
    """
```

## Module Design

**Prefer module-level functions:**
Per CLAUDE.md guidelines, use functions rather than classes when appropriate:

```python
# Module-level function (preferred for simple operations)
def run_scrapy(config: DownloadConfig) -> None:
    """使用 subprocess 调用 scrapy crawl 命令运行爬虫"""
    ...

def validate_downloads(directory: str) -> tuple[bool, dict]:
    """校验下载的文件"""
    ...

def merge_ts_files(directory: str, output_file: str | None = None) -> bool:
    """合并 ts 文件为 mp4"""
    ...

# Class for complex stateful operations
class DatabaseManager:
    """需要管理连接状态，使用类"""
    ...

class AutoDownloader:
    """需要管理守护进程循环状态，使用类"""
    ...
```

**Single responsibility classes:**
```python
class FFmpegChecker:
    """检查 ffmpeg 是否可用（单一职责）"""
    @staticmethod
    def is_available() -> bool: ...

class TSFileCollector:
    """获取目录中所有 .ts 文件并按约定排序"""
    @staticmethod
    def collect(directory: str) -> list[str]: ...
```

## Signal Handling

**Daemon Pattern:**
```python
import signal
import sys

class AutoDownloader:
    def __init__(self, config: AutoDownloadConfig) -> None:
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._running = True

    def _signal_handler(self, signum, frame) -> None:
        """处理中断信号（Ctrl+C）"""
        if self._running:
            logger.warning("\n\n⚠️  收到中断信号，正在优雅退出...")
            self._running = False
        else:
            logger.error("\n\n⚠️  再次收到中断信号，强制退出...")
            sys.exit(1)
```

## Context Managers

**Database Connection:**
```python
class DatabaseManager:
    def __enter__(self) -> DatabaseManager:
        """上下文管理器：进入"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器：退出"""
        self.close()
```

**Usage:**
```python
with DatabaseManager(...) as db:
    tasks = db.get_pending_tasks()
```

## Entry Points

**CLI Entry Pattern:**
```python
# cli/main.py
def main() -> None:
    """主入口"""
    config = _parse_args()
    _print_header(config)
    recovery_result = recover_download(config)
    if recovery_result.is_complete:
        _print_footer(config)
        return
    sys.exit(1)


if __name__ == "__main__":
    main()
```

**Module Entry Pattern:**
```python
# m3u8_spider/core/validator.py
def main() -> None:
    """主函数"""
    if len(sys.argv) < 2:
        logger.error("用法: python -m m3u8_spider.core.validator <目录>")
        sys.exit(1)
    directory = _resolve_directory(sys.argv[1])
    is_complete, _result = validate_downloads(directory)
    sys.exit(0 if is_complete else 1)


if __name__ == "__main__":
    main()
```

**Package entry points (pyproject.toml):**
```toml
[project.scripts]
m3u8-download = "cli.main:main"
m3u8-daemon = "cli.daemon:main"
m3u8-batch-merge = "cli.batch_merge:main"
m3u8-refresh = "cli.m3u8_refresh_daemon:main"
```

## Linting Commands

```bash
# Check all files
ruff check .

# Auto-fix issues
ruff check --fix .

# Format imports only
ruff check --select I --fix .

# Check specific file
ruff check m3u8_spider/core/downloader.py
```

## Section Comments

**Use #-style section separators:**
```python
# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class DownloadConfig:
    ...


# ---------------------------------------------------------------------------
# Scrapy 运行函数
# ---------------------------------------------------------------------------


def run_scrapy(config: DownloadConfig) -> None:
    ...
```

---

*Convention analysis: 2026-03-29*