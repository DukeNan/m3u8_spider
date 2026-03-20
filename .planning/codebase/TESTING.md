# Testing Patterns

**Analysis Date:** 2026-03-20

## Current State

**⚠️ No tests exist in this codebase.**

The codebase currently lacks:
- Test files (`test_*.py` or `*_test.py`)
- Test configuration (pytest.ini, tox.ini)
- Test dependencies (pytest, pytest-cov)
- Mocking utilities

## Framework Recommendations

Given the project's technology stack, the recommended testing approach would be:

### Primary: pytest

**Installation:**
```bash
pip install pytest pytest-cov pytest-mock
```

**Config in pyproject.toml:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["m3u8_spider"]
omit = ["*/tests/*", "*/scrapy_project/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Test Directory Structure

**Recommended location:** `.planning/codebase/` structure already exists, but tests should be placed at project root:

```
m3u8_spider/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── core/
│   │   ├── __init__.py
│   │   ├── test_downloader.py
│   │   ├── test_validator.py
│   │   └── test_recovery.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── test_manager.py
│   └── utils/
│       ├── __init__.py
│       └── test_merger.py
```

## Test Structure Patterns

### Unit Test Example (for validator.py)

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

    def test_parse_with_valid_playlist(self, temp_dir):
        """测试解析有效的 playlist 文件"""
        playlist_path = temp_dir / "playlist.txt"
        playlist_path.write_text(
            "https://example.com/seg1.ts\n"
            "https://example.com/seg2.ts\n"
        )
        
        segments = PlaylistParser.parse(str(playlist_path))
        
        assert len(segments) == 2
        assert segments[0].url == "https://example.com/seg1.ts"
        assert segments[0].index == 0

    def test_parse_with_missing_file(self):
        """测试解析不存在的文件"""
        segments = PlaylistParser.parse("/nonexistent/path/playlist.txt")
        assert segments == []

    def test_parse_skips_comments(self, temp_dir):
        """测试跳过注释行"""
        playlist_path = temp_dir / "playlist.txt"
        playlist_path.write_text(
            "#EXTM3U\n"
            "#EXTINF:10.0,\n"
            "https://example.com/seg1.ts\n"
        )
        
        segments = PlaylistParser.parse(str(playlist_path))
        assert len(segments) == 1


class TestValidationResult:
    """测试 ValidationResult 数据类"""

    def test_is_complete_with_all_files(self):
        """测试完整校验通过"""
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

    def test_is_complete_with_missing_files(self):
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
```

### Fixture Pattern (conftest.py)

```python
from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from dataclasses import dataclass


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_playlist(temp_dir):
    """创建示例 playlist 文件"""
    playlist_path = temp_dir / "playlist.txt"
    content = "#EXTM3U\n" + "\n".join(
        f"https://example.com/segment_{i:05d}.ts" for i in range(10)
    )
    playlist_path.write_text(content)
    return playlist_path


@pytest.fixture
def sample_content_lengths(temp_dir):
    """创建示例 content_lengths.json"""
    content_lengths_path = temp_dir / "content_lengths.json"
    data = {f"segment_{i:05d}.ts": 1024000 for i in range(10)}
    content_lengths_path.write_text(json.dumps(data))
    return content_lengths_path


@dataclass
class MockDownloadConfig:
    """模拟下载配置"""
    m3u8_url: str = "https://example.com/playlist.m3u8"
    filename: str = "test_video"
    concurrent: int = 32
    delay: float = 0.0
    metadata_only: bool = False
    retry_urls: list | None = None
```

## Mocking Patterns

### Mocking Database Connections

```python
from unittest.mock import Mock, patch, MagicMock


def test_database_manager_get_pending_tasks(mocker):
    """测试获取待下载任务"""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    mock_cursor.fetchall.return_value = [
        {"id": 1, "number": "001", "m3u8_address": "http://x.m3u8", "status": 0},
    ]
    
    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    
    with patch("m3u8_spider.database.manager.pymysql.connect", return_value=mock_connection):
        from m3u8_spider.database.manager import DatabaseManager
        
        db = DatabaseManager(host="localhost", port=3306, user="root", password="", database="test")
        tasks = db.get_pending_tasks(limit=10)
        
        assert len(tasks) == 1
        assert tasks[0].id == 1
        assert tasks[0].number == "001"
```

### Mocking Scrapy Downloads

```python
from unittest.mock import Mock, patch


def test_run_scrapy_with_config(mocker):
    """测试 Scrapy 运行函数"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = Mock(returncode=0)
    
    from m3u8_spider.core.downloader import DownloadConfig, run_scrapy
    
    config = DownloadConfig(
        m3u8_url="https://example.com/video.m3u8",
        filename="test",
    )
    
    run_scrapy(config)
    
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "scrapy" in args
    assert "crawl" in args
    assert "m3u8_downloader" in args
```

### Mocking File System

```python
def test_download_dir_creation(temp_dir):
    """测试下载目录自动创建"""
    from m3u8_spider.core.downloader import DownloadConfig
    
    config = DownloadConfig(
        m3u8_url="https://example.com/video.m3u8",
        filename="test_video",
    )
    
    # 验证 download_dir 属性
    assert "test_video" in str(config.download_dir)
    assert config.sanitized_filename == "test_video"
```

## Integration Test Pattern

```python
import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """模拟环境变量"""
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "test")
    monkeypatch.setenv("MYSQL_PASSWORD", "test")
    monkeypatch.setenv("MYSQL_DATABASE", "test_db")


def test_download_flow_integration(temp_dir, mock_env, mocker):
    """集成测试：下载流程"""
    # Mock subprocess.run to avoid actual scrapy execution
    mocker.patch("subprocess.run", return_value=Mock(returncode=0))
    
    # Create mock playlist and content_lengths
    playlist_path = temp_dir / "playlist.txt"
    playlist_path.write_text("https://example.com/seg1.ts\n")
    
    # Test recovery flow would go here
    pass
```

## Coverage Commands

```bash
# Run tests with coverage
pytest --cov=m3u8_spider --cov-report=term-missing

# Generate HTML report
pytest --cov=m3u8_spider --cov-report=html

# Run specific test file
pytest tests/core/test_validator.py -v

# Run tests matching pattern
pytest -k "test_parse" -v
```

## What to Test

### High Priority

1. **DownloadValidator** (`m3u8_spider/core/validator.py`)
   - `PlaylistParser.parse()`
   - `ContentLengthLoader.load()`
   - `DownloadValidator.validate()`
   - `ValidationResult` properties

2. **DownloadConfig** (`m3u8_spider/core/downloader.py`)
   - URL validation in `__post_init__`
   - Filename sanitization
   - Property calculations

3. **DatabaseManager** (`m3u8_spider/database/manager.py`)
   - Connection handling
   - Task queries
   - Status updates

### Medium Priority

4. **MP4Merger** (`m3u8_spider/utils/merger.py`)
   - FFmpeg availability check
   - File collection and sorting
   - Encryption handling

5. **UrlResolver** (`scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`)
   - Relative URL resolution
   - Absolute URL passthrough

## What NOT to Mock

- Standard library modules (`pathlib`, `json`, `subprocess`)
- Third-party modules that are fast/safe (`dataclasses`, `argparse`)
- Modules under test (test the real thing when possible)

## When to Use Mocks

- **Database connections**: Always mock `pymysql.connect`
- **Subprocess calls**: Mock `subprocess.run`, `scrapy` commands
- **External services**: Mock HTTP calls
- **File I/O that creates real files**: Use `tempfile` fixtures instead of mocks

---

*Testing analysis: 2026-03-20*
