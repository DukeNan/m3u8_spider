# Testing Patterns

**Analysis Date:** 2026-03-29

## Current State

**No tests exist in this codebase.**

The codebase currently lacks:
- Test files (`test_*.py` or `*_test.py`)
- Test configuration (`pytest.ini`, `conftest.py`)
- Test dependencies (`pytest`, `pytest-cov`, `pytest-mock`)
- Mocking utilities
- CI/CD integration for testing

## Recommended Test Framework

### pytest

**Installation:**
```bash
source .venv/bin/activate && uv pip install pytest pytest-cov pytest-mock
```

**Config in `pyproject.toml`:**
```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "pytest-mock>=3.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["m3u8_spider", "cli"]
omit = ["*/tests/*", "*/scrapy_project/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Test Directory Structure

**Recommended location:** Project root, separate from source code

```
m3u8_spider/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── core/
│   │   ├── __init__.py
│   │   ├── test_downloader.py   # DownloadConfig, run_scrapy
│   │   ├── test_validator.py    # PlaylistParser, DownloadValidator
│   │   └── test_recovery.py     # recover_download, metadata handling
│   │   └── test_m3u8_fetcher.py # M3U8 fetching logic
│   ├── database/
│   │   ├── __init__.py
│   │   └── test_manager.py      # DatabaseManager, DownloadTask
│   ├── automation/
│   │   ├── __init__.py
│   │   ├── test_auto_downloader.py  # AutoDownloader
│   │   └── test_m3u8_refresher.py   # M3U8 refresher
│   ├── utils/
│   │   ├── __init__.py
│   │   └── test_merger.py       # MP4Merger, EncryptionInfo
│   │   └── test_migration.py    # Migration utilities
│   └── cli/
│   │   ├── __init__.py
│   │   ├── test_main.py         # CLI argument parsing
│   │   ├── test_daemon.py       # Daemon entry point
│   │   └── test_batch_merge.py  # Batch merge logic
│   └── scrapy_project/
│       ├── __init__.py
│       └── test_m3u8_downloader.py  # Spider logic (UrlResolver, EncryptionDetector)
```

## Test Structure Patterns

### Standard Test Class Pattern

```python
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json

from m3u8_spider.core.validator import (
    PlaylistParser,
    ContentLengthLoader,
    DownloadValidator,
    ValidationResult,
)


class TestPlaylistParser:
    """测试 PlaylistParser 类"""

    def test_parse_with_valid_playlist(self, temp_dir: Path) -> None:
        """测试解析有效的 playlist 文件"""
        playlist_path = temp_dir / "playlist.txt"
        playlist_path.write_text(
            "https://example.com/seg1.ts\n"
            "https://example.com/seg2.ts\n"
        )

        segments = PlaylistParser.parse(str(playlist_path))

        assert len(segments) == 2
        assert segments[0].url == "https://example.com/seg1.ts"
        assert segments[0].expected_filename == "seg1.ts"
        assert segments[0].index == 0

    def test_parse_with_missing_file(self) -> None:
        """测试解析不存在的文件"""
        segments = PlaylistParser.parse("/nonexistent/path/playlist.txt")
        assert segments == []

    def test_parse_skips_comments(self, temp_dir: Path) -> None:
        """测试跳过注释行"""
        playlist_path = temp_dir / "playlist.txt"
        playlist_path.write_text(
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXTINF:10.0,\n"
            "https://example.com/seg1.ts\n"
        )

        segments = PlaylistParser.parse(str(playlist_path))
        assert len(segments) == 1

    def test_parse_generates_filename_for_non_ts_urls(self, temp_dir: Path) -> None:
        """测试非 TS URL 的文件名生成"""
        playlist_path = temp_dir / "playlist.txt"
        playlist_path.write_text("https://example.com/segment\n")

        segments = PlaylistParser.parse(str(playlist_path))
        assert segments[0].expected_filename == "segment_00000.ts"
```

### Dataclass Test Pattern

```python
from m3u8_spider.core.downloader import DownloadConfig
from m3u8_spider.core.validator import ValidationResult


class TestDownloadConfig:
    """测试 DownloadConfig 数据类"""

    def test_valid_config_creation(self) -> None:
        """测试创建有效配置"""
        config = DownloadConfig(
            m3u8_url="https://example.com/video.m3u8",
            filename="test_video",
        )
        assert config.m3u8_url == "https://example.com/video.m3u8"
        assert config.sanitized_filename == "test_video"

    def test_invalid_url_raises_error(self) -> None:
        """测试无效 URL 抛出 ValueError"""
        with pytest.raises(ValueError, match="无效的URL"):
            DownloadConfig(m3u8_url="invalid_url", filename="test")

    def test_empty_filename_raises_error(self) -> None:
        """测试空文件名抛出 ValueError"""
        with pytest.raises(ValueError, match="文件名不能为空"):
            DownloadConfig(m3u8_url="https://example.com/video.m3u8", filename="")

    def test_metadata_only_and_retry_urls_conflict(self) -> None:
        """测试 metadata_only 与 retry_urls 互斥"""
        with pytest.raises(ValueError, match="不能同时启用"):
            DownloadConfig(
                m3u8_url="https://example.com/video.m3u8",
                filename="test",
                metadata_only=True,
                retry_urls=[{"url": "https://example.com/seg.ts", "filename": "seg.ts"}],
            )

    def test_sanitized_filename_removes_invalid_chars(self) -> None:
        """测试文件名清理"""
        config = DownloadConfig(
            m3u8_url="https://example.com/video.m3u8",
            filename='test<>:"/\\|?*video',
        )
        assert config.sanitized_filename == "test___________video"


class TestValidationResult:
    """测试 ValidationResult 数据类"""

    def test_is_complete_with_all_files(self) -> None:
        """测试校验通过"""
        result = ValidationResult(
            directory="/test",
            expected_count=10,
            actual_count=10,
            total_size=1000000,
            missing_files=[],
            zero_size_files=[],
            incomplete_files=[],
        )
        assert result.is_complete is True

    def test_is_complete_with_missing_files(self) -> None:
        """测试有缺失文件"""
        result = ValidationResult(
            directory="/test",
            expected_count=10,
            actual_count=8,
            total_size=800000,
            missing_files=["seg3.ts", "seg4.ts"],
            zero_size_files=[],
            incomplete_files=[],
        )
        assert result.is_complete is False

    def test_failed_files_combines_all_failures(self) -> None:
        """测试 failed_files 属性合并所有失败"""
        result = ValidationResult(
            directory="/test",
            expected_count=10,
            actual_count=5,
            total_size=500000,
            missing_files=["seg1.ts", "seg2.ts"],
            zero_size_files=["seg3.ts"],
            incomplete_files=["seg4.ts"],
        )
        assert set(result.failed_files) == {"seg1.ts", "seg2.ts", "seg3.ts", "seg4.ts"}
```

## Fixture Patterns

### conftest.py

```python
from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
import json
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass


@pytest.fixture
def temp_dir() -> Path:
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_playlist(temp_dir: Path) -> Path:
    """创建示例 playlist 文件"""
    playlist_path = temp_dir / "playlist.txt"
    content = "#EXTM3U\n" + "\n".join(
        f"https://example.com/segment_{i:05d}.ts" for i in range(10)
    )
    playlist_path.write_text(content)
    return playlist_path


@pytest.fixture
def sample_content_lengths(temp_dir: Path) -> Path:
    """创建示例 content_lengths.json"""
    content_lengths_path = temp_dir / "content_lengths.json"
    data = {f"segment_{i:05d}.ts": 1024000 for i in range(10)}
    content_lengths_path.write_text(json.dumps(data))
    return content_lengths_path


@pytest.fixture
def sample_encryption_info(temp_dir: Path) -> Path:
    """创建示例 encryption_info.json"""
    encryption_path = temp_dir / "encryption_info.json"
    data = {
        "is_encrypted": True,
        "method": "AES-128",
        "key_uri": "https://example.com/key.key",
        "key_file": "encryption.key",
        "iv": None,
    }
    encryption_path.write_text(json.dumps(data))
    return encryption_path


@pytest.fixture
def sample_ts_files(temp_dir: Path) -> list[Path]:
    """创建示例 TS 文件"""
    ts_files = []
    for i in range(5):
        ts_path = temp_dir / f"segment_{i:05d}.ts"
        ts_path.write_bytes(b"\x00" * 1024000)  # 1MB of zeros
        ts_files.append(ts_path)
    return ts_files


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """模拟环境变量"""
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "test_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "test_pass")
    monkeypatch.setenv("MYSQL_DATABASE", "test_db")


@pytest.fixture
def mock_subprocess_run(mocker: pytest.MockerFixture) -> Mock:
    """模拟 subprocess.run"""
    return mocker.patch("subprocess.run", return_value=Mock(returncode=0))


@pytest.fixture
def mock_db_connection(mocker: pytest.MockerFixture) -> MagicMock:
    """模拟数据库连接"""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.ping.return_value = True

    mocker.patch("pymysql.connect", return_value=mock_conn)
    return mock_conn
```

## Mocking Patterns

### Database Operations

```python
from unittest.mock import Mock, patch, MagicMock
from m3u8_spider.database.manager import DatabaseManager, DownloadTask


class TestDatabaseManager:
    """测试 DatabaseManager"""

    def test_connect_success(self, mocker: pytest.MockerFixture) -> None:
        """测试成功连接"""
        mock_connect = mocker.patch("pymysql.connect", return_value=MagicMock())

        db = DatabaseManager(
            host="localhost", port=3306, user="root", password="", database="test"
        )
        result = db.connect()

        assert result is True
        mock_connect.assert_called_once()

    def test_get_pending_tasks(self, mock_db_connection: MagicMock) -> None:
        """测试获取待下载任务"""
        mock_cursor = mock_db_connection.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "number": "001", "m3u8_address": "http://x.m3u8", "status": 0, "title": None, "provider": None},
            {"id": 2, "number": "002", "m3u8_address": "http://y.m3u8", "status": 0, "title": "Video", "provider": "ProviderA"},
        ]

        db = DatabaseManager(
            host="localhost", port=3306, user="root", password="", database="test"
        )
        db._connection = mock_db_connection

        tasks = db.get_pending_tasks(limit=10)

        assert len(tasks) == 2
        assert tasks[0].id == 1
        assert tasks[0].number == "001"
        assert tasks[1].title == "Video"

    def test_update_task_status_success(self, mock_db_connection: MagicMock) -> None:
        """测试更新任务状态成功"""
        mock_cursor = mock_db_connection.cursor.return_value
        mock_cursor.rowcount = 1

        db = DatabaseManager(
            host="localhost", port=3306, user="root", password="", database="test"
        )
        db._connection = mock_db_connection

        result = db.update_task_status(task_id=1, status=1)

        assert result is True

    def test_update_task_status_failure(self, mock_db_connection: MagicMock) -> None:
        """测试更新任务状态失败"""
        mock_cursor = mock_db_connection.cursor.return_value
        mock_cursor.execute.side_effect = pymysql.Error("Connection lost")

        db = DatabaseManager(
            host="localhost", port=3306, user="root", password="", database="test"
        )
        db._connection = mock_db_connection

        result = db.update_task_status(task_id=1, status=1)

        assert result is False
```

### Subprocess Calls

```python
from m3u8_spider.core.downloader import DownloadConfig, run_scrapy


class TestRunScrapy:
    """测试 run_scrapy 函数"""

    def test_run_scrapy_calls_subprocess(
        self, mock_subprocess_run: Mock, temp_dir: Path
    ) -> None:
        """测试 run_scrapy 调用 subprocess"""
        # Create necessary directories
        movies_dir = temp_dir / "movies"
        movies_dir.mkdir(parents=True)
        logs_dir = temp_dir / "logs"
        logs_dir.mkdir(parents=True)

        config = DownloadConfig(
            m3u8_url="https://example.com/video.m3u8",
            filename="test_video",
        )

        # Patch project_root calculation
        with patch.object(config, "project_root", temp_dir):
            run_scrapy(config)

        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert "scrapy" in args
        assert "crawl" in args
        assert "m3u8_downloader" in args

    def test_run_scrapy_with_retry_urls(
        self, mock_subprocess_run: Mock, temp_dir: Path
    ) -> None:
        """测试带 retry_urls 的 run_scrapy"""
        movies_dir = temp_dir / "movies"
        movies_dir.mkdir(parents=True)
        logs_dir = temp_dir / "logs"
        logs_dir.mkdir(parents=True)

        config = DownloadConfig(
            m3u8_url="https://example.com/video.m3u8",
            filename="test_video",
            retry_urls=[
                {"url": "https://example.com/seg1.ts", "filename": "seg1.ts"}
            ],
        )

        with patch.object(config, "project_root", temp_dir):
            run_scrapy(config)

        args = mock_subprocess_run.call_args[0][0]
        # retry_urls should be JSON-encoded in command
        assert any("retry_urls" in str(arg) for arg in args)
```

### File System (Use fixtures, not mocks)

```python
from m3u8_spider.core.validator import DownloadValidator


class TestDownloadValidator:
    """测试 DownloadValidator"""

    def test_validate_complete_download(
        self, temp_dir: Path, sample_playlist: Path, sample_ts_files: list[Path], sample_content_lengths: Path
    ) -> None:
        """测试完整下载校验"""
        validator = DownloadValidator(str(temp_dir))
        result = validator.validate()

        assert result is not None
        assert result.expected_count == 10
        assert result.actual_count == 5  # Only 5 TS files created
        assert result.is_complete is False  # Not complete (missing files)

    def test_validate_missing_playlist(self, temp_dir: Path) -> None:
        """测试缺失 playlist 文件"""
        validator = DownloadValidator(str(temp_dir))
        result = validator.validate()

        assert result is None  # Returns None when playlist missing

    def test_validate_empty_ts_file(
        self, temp_dir: Path, sample_playlist: Path, sample_content_lengths: Path
    ) -> None:
        """测试空 TS 文件"""
        empty_ts = temp_dir / "segment_00000.ts"
        empty_ts.write_bytes(b"")  # 0 bytes

        validator = DownloadValidator(str(temp_dir))
        result = validator.validate()

        assert result is not None
        assert "segment_00000.ts" in result.zero_size_files
```

## Test Categories

### Unit Tests

**Scope:** Individual functions, methods, and classes

**Key test targets:**

| Module | File | Key Functions/Classes |
|--------|------|----------------------|
| `m3u8_spider.core.validator` | `validator.py` | `PlaylistParser`, `ContentLengthLoader`, `DownloadValidator`, `ValidationResult` |
| `m3u8_spider.core.downloader` | `downloader.py` | `DownloadConfig`, `run_scrapy` |
| `m3u8_spider.core.recovery` | `recovery.py` | `recover_download`, `_collect_missing_metadata`, `_build_retry_urls` |
| `m3u8_spider.database.manager` | `manager.py` | `DatabaseManager`, `DownloadTask` |
| `m3u8_spider.utils.merger` | `merger.py` | `MP4Merger`, `EncryptionInfo`, `FFmpegChecker` |
| `scrapy_project.m3u8_spider.spiders.m3u8_downloader` | `m3u8_downloader.py` | `UrlResolver`, `EncryptionDetector` |

### Integration Tests

**Scope:** Multiple components working together

```python
class TestRecoveryFlow:
    """测试恢复流程集成"""

    def test_recovery_with_missing_metadata(
        self, temp_dir: Path, mock_subprocess_run: Mock, mock_env: None
    ) -> None:
        """测试缺失元数据的恢复流程"""
        # Setup: create partial download with missing metadata
        movies_dir = temp_dir / "movies" / "test_video"
        movies_dir.mkdir(parents=True)
        (movies_dir / "segment_00000.ts").write_bytes(b"\x00" * 1024)

        config = DownloadConfig(
            m3u8_url="https://example.com/video.m3u8",
            filename="test_video",
        )

        with patch.object(config, "project_root", temp_dir):
            # Mock validation to return incomplete
            with patch("m3u8_spider.core.recovery.validate_downloads", return_value=(False, {"failed_urls": {"seg.ts": "https://example.com/seg.ts"}})):
                result = recover_download(config)

        # Should have attempted metadata download
        assert mock_subprocess_run.call_count >= 1
```

### CLI Tests

```python
from cli.main import _parse_args, main


class TestCLI:
    """测试 CLI 入口"""

    def test_parse_args_valid(self) -> None:
        """测试有效参数解析"""
        config = _parse_args(["https://example.com/video.m3u8", "test_video"])
        assert config.m3u8_url == "https://example.com/video.m3u8"
        assert config.filename == "test_video"

    def test_parse_args_with_options(self) -> None:
        """测试带可选参数"""
        config = _parse_args([
            "https://example.com/video.m3u8",
            "test_video",
            "--concurrent", "16",
            "--delay", "0.5",
        ])
        assert config.concurrent == 16
        assert config.delay == 0.5

    def test_parse_args_invalid_url_exits(self, mocker: pytest.MockerFixture) -> None:
        """测试无效 URL 退出"""
        mock_exit = mocker.patch("sys.exit")
        _parse_args(["invalid_url", "test"])
        mock_exit.assert_called_once_with(1)
```

## Run Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/core/test_validator.py

# Run tests matching pattern
pytest -k "test_parse"

# Run with coverage
pytest --cov=m3u8_spider --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=m3u8_spider --cov-report=html

# Run specific test class
pytest tests/core/test_validator.py::TestPlaylistParser

# Run with markers (if defined)
pytest -m "not slow"
```

## Test Coverage Priorities

### High Priority (Core functionality)

1. **DownloadValidator** (`m3u8_spider/core/validator.py`)
   - Playlist parsing logic
   - Content-Length validation
   - File existence checking
   - Result aggregation

2. **DownloadConfig** (`m3u8_spider/core/downloader.py`)
   - URL validation
   - Filename sanitization
   - Config immutability
   - Property calculations

3. **Recovery flow** (`m3u8_spider/core/recovery.py`)
   - Metadata detection
   - Retry URL building
   - Round-based retry logic

4. **DatabaseManager** (`m3u8_spider/database/manager.py`)
   - Connection handling
   - Task queries
   - Status updates

### Medium Priority

5. **UrlResolver** (`scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`)
   - Relative URL resolution
   - Absolute URL passthrough

6. **EncryptionDetector** (`scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`)
   - Encryption detection from playlist
   - Fallback regex parsing

7. **MP4Merger** (`m3u8_spider/utils/merger.py`)
   - FFmpeg availability check
   - File collection and sorting
   - Encryption handling

### Lower Priority

8. **CLI entry points** (`cli/*.py`)
   - Argument parsing
   - Error handling

9. **AutoDownloader** (`m3u8_spider/automation/auto_downloader.py`)
   - Daemon loop behavior
   - Signal handling

## What to Mock

**Always mock:**
- Database connections (`pymysql.connect`)
- Subprocess calls (`subprocess.run` for Scrapy execution)
- External HTTP requests (if any)
- FFmpeg availability (`FFmpegChecker.is_available`)

**Use fixtures instead of mocks:**
- File system operations (use `tempfile`)
- JSON file reading/writing
- Path operations

**Never mock:**
- Standard library modules (`pathlib`, `json`, `re`)
- Dataclasses (they are simple and fast)
- Pure functions with no external dependencies

---

*Testing analysis: 2026-03-29*