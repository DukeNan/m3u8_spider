"""utils/helpers 单元测试"""

from __future__ import annotations

from pathlib import Path

from m3u8_spider.utils.helpers import resolve_directory


class TestResolveDirectory:
    """resolve_directory() 的单元测试"""

    def test_absolute_path_returns_as_is(self) -> None:
        result = resolve_directory("/absolute/path/to/video")
        assert result == "/absolute/path/to/video"

    def test_relative_path_with_separator_returns_as_is(self) -> None:
        result = resolve_directory("relative/path/to/video")
        assert result == "relative/path/to/video"

    def test_relative_path_with_backslash_returns_as_is(self) -> None:
        result = resolve_directory("relative\\path")
        assert result == "relative\\path"

    def test_video_name_resolves_to_movies_dir(self) -> None:
        result = resolve_directory("my_video")
        assert result.endswith("/movies/my_video")
