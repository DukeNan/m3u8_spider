# Coding Conventions

**Analysis Date:** 2026-03-20

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
- E/F/W: Pyflakes/ pycodestyle errors/warnings
- I: Import sorting (isort rules)
- UP: Python 3.x upgrade rules
- B: Flake8 bugbear rules

## Naming Patterns

**Files:**
- Python modules: `snake_case.py`
- Test files: `test_*.py` or `*_test.py` (not currently used)

**Classes:**
- PascalCase
- Examples: `DownloadConfig`, `DatabaseManager`, `AutoDownloader`, `MP4Merger`

**Functions/Methods:**
- snake_case
- Private methods prefixed with `_`
- Examples: `_parse_args()`, `recover_download()`, `_ensure_connection()`

**Variables:**
- snake_case
- Examples: `download_dir`, `m3u8_url`, `retry_rounds`

**Constants:**
- UPPER_SNAKE_CASE
- Module-level: `DEFAULT_CONCURRENT`, `INVALID_FILENAME_CHARS`
- Examples: `CONTENT_LENGTHS_FILE`, `LOGS_DIR`

**Type Variables:**
- PascalCase in generic contexts
- Union syntax: `list[str] | None` (Python 3.10+)

## Code Style

**File Header (Scripts):**
```python
#!/usr/bin/env python3
"""
模块描述
"""

from __future__ import annotations
```

**Required Import:**
```python
from __future__ import annotations
```
- Placed after docstring, before other imports
- Enables forward references and modern type syntax

## Import Organization

**Order (enforced by ruff I001):**
1. `from __future__ import annotations`
2. Standard library imports (`import os`, `import sys`)
3. Third-party imports (`import scrapy`, `import pymysql`)
4. Local imports (`from m3u8_spider.config import ...`)

**Multi-line Imports:**
```python
from m3u8_spider.config import (
    DEFAULT_CONCURRENT,
    DEFAULT_DELAY,
    DOWNLOAD_COOLDOWN_SECONDS,
    get_mysql_config,
)
```

**Common Issue:** Import sorting errors - run `ruff check --fix` to auto-fix.

## Type Hints

**Union Syntax (Python 3.10+):**
```python
def func(x: str | None) -> list[dict] | None:
    pass
```

**Dataclass with Types:**
```python
@dataclass
class DownloadConfig:
    m3u8_url: str
    filename: str
    concurrent: int = DEFAULT_CONCURRENT
    metadata_only: bool = False
    retry_urls: list[dict] | None = None
```

**Properties:**
```python
@property
def sanitized_filename(self) -> str:
    """清理后的文件名"""
    return self.filename.strip()
```

## Dataclass Usage

**Immutable Config (frozen=True):**
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
```

## Path Handling

**Always use pathlib.Path:**
```python
from pathlib import Path

# 构建路径
download_dir = project_root / DEFAULT_BASE_DIR / self.sanitized_filename

# 创建目录
download_dir.mkdir(parents=True, exist_ok=True)

# 读写文件
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
```

**Absolute Path Resolution:**
```python
project_root = Path(__file__).resolve().parent.parent.parent
```

## Logging

**Initialization Pattern:**
```python
from m3u8_spider.logger import get_logger

logger = get_logger(__name__)
```

**Log Format:**
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Usage:**
```python
logger.info(f"下载目录: {download_dir}")
logger.warning(f"⚠️  检测到缺失文件: {filename}")
logger.error(f"❌ 下载失败: {e}")
```

**Context Manager for DB:**
```python
with DatabaseManager(...) as db:
    tasks = db.get_pending_tasks()
```

## Error Handling

**Validation with ValueError:**
```python
def __post_init__(self) -> None:
    if not self.m3u8_url.startswith(("http://", "https://")):
        raise ValueError(f"无效的URL: {self.m3u8_url}")
```

**Graceful Degradation:**
```python
try:
    data = json.load(f)
except Exception:
    return {}  # 返回默认值而非抛出
```

**Context Managers:**
```python
try:
    self._connection = pymysql.connect(**self._config)
    return True
except pymysql.Error as e:
    logger.error(f"❌ 数据库连接失败: {e}")
    return False
```

## Docstrings

**Module Docstring:**
```python
"""
模块描述
负责...
"""
```

**Class Docstring:**
```python
class DatabaseManager:
    """MySQL 数据库管理器，负责连接池和所有数据库操作"""
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
```

## Signal Handling

**Daemon Pattern:**
```python
signal.signal(signal.SIGINT, self._signal_handler)
signal.signal(signal.SIGTERM, self._signal_handler)

def _signal_handler(self, signum, frame) -> None:
    if self._running:
        logger.warning("⚠️  收到中断信号，正在优雅退出...")
        self._running = False
    else:
        logger.error("⚠️  再次收到中断信号，强制退出...")
        sys.exit(1)
```

## Context Managers

**DB Connection:**
```python
class DatabaseManager:
    def __enter__(self) -> DatabaseManager:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
```

## Entry Points

**CLI Entry Pattern:**
```python
if __name__ == "__main__":
    main()
```

**Module Entry Pattern:**
```python
def main() -> None:
    """主入口"""
    pass
```

## Linting Commands

```bash
# Check all files
ruff check .

# Auto-fix issues
ruff check --fix .

# Format imports only
ruff check --select I --fix .
```

---

*Convention analysis: 2026-03-20*
