"""pytest 共享 fixtures"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 添加 scrapy_project 到 Python 路径，使 scrapy 包可导入
_scrapy_project = Path(__file__).resolve().parent.parent / "scrapy_project"
if str(_scrapy_project) not in sys.path:
    sys.path.insert(0, str(_scrapy_project))


@pytest.fixture
def playlist_content() -> str:
    """标准 M3U8 playlist 内容"""
    return """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXTINF:10.0,
https://example.com/segments/segment_00001.ts
#EXTINF:10.0,
https://example.com/segments/segment_00002.ts
#EXTINF:10.0,
https://example.com/segments/segment_00003.ts
#EXT-X-ENDLIST
"""


@pytest.fixture
def playlist_with_relative_urls() -> str:
    """使用相对路径的 playlist"""
    return """#EXTM3U
#EXT-X-VERSION:3
#EXTINF:10.0,
segment_00001.ts
#EXTINF:10.0,
segment_00002.ts
#EXT-X-ENDLIST
"""


@pytest.fixture
def encrypted_playlist_content() -> str:
    """AES-128 加密的 M3U8"""
    return """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key/encryption.key",IV=0x1234567890abcdef
#EXTINF:10.0,
https://example.com/segments/segment_00001.ts
#EXTINF:10.0,
https://example.com/segments/segment_00002.ts
#EXT-X-ENDLIST
"""


@pytest.fixture
def empty_playlist_content() -> str:
    """"""


@pytest.fixture
def playlist_dir(tmp_path: Path, playlist_content: str) -> Path:
    """创建含 playlist.txt 的临时下载目录"""
    d = tmp_path / "test_video"
    d.mkdir()
    (d / "playlist.txt").write_text(playlist_content, encoding="utf-8")
    return d


@pytest.fixture
def playlist_dir_with_ts(playlist_dir: Path) -> Path:
    """创建含 playlist.txt 和部分 ts 文件的临时目录"""
    for i in range(1, 4):
        ts_path = playlist_dir / f"segment_{i:05d}.ts"
        ts_path.write_bytes(b"x" * 1000)
    return playlist_dir


@pytest.fixture
def playlist_dir_with_content_lengths(playlist_dir_with_ts: Path) -> Path:
    """添加 content_lengths.json"""
    lengths = {"segment_00001.ts": 1000, "segment_00002.ts": 1000, "segment_00003.ts": 1000}
    (playlist_dir_with_ts / "content_lengths.json").write_text(
        json.dumps(lengths), encoding="utf-8"
    )
    return playlist_dir_with_ts


@pytest.fixture
def m3u8_content_simple() -> str:
    """简单的 M3U8 用于加密检测"""
    return "#EXTM3U\n#EXTINF:10.0,\nhttps://example.com/seg.ts\n#EXT-X-ENDLIST\n"


@pytest.fixture
def m3u8_content_encrypted() -> str:
    """AES-128 加密的 M3U8 内容"""
    return (
        '#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="https://key.example.com/key",IV=0xabc\n'
        "#EXTINF:10.0,\nhttps://example.com/seg.ts\n#EXT-X-ENDLIST\n"
    )


@pytest.fixture
def m3u8_content_none_key() -> str:
    """包含 METHOD=NONE 的 M3U8（表示某片段未加密）"""
    return (
        '#EXTM3U\n#EXT-X-KEY:METHOD=NONE\n'
        "#EXTINF:10.0,\nhttps://example.com/seg1.ts\n"
        '#EXT-X-KEY:METHOD=AES-128,URI="https://key.example.com/key"\n'
        "#EXTINF:10.0,\nhttps://example.com/seg2.ts\n"
        "#EXT-X-ENDLIST\n"
    )
