from __future__ import annotations

from pathlib import Path

from m3u8_spider.config import DEFAULT_BASE_DIR


def resolve_directory(arg: str) -> str:
    """将视频名解析为 movies/<name> 目录，绝对路径或含分隔符则原样返回。"""
    if Path(arg).is_absolute():
        return arg
    if "/" in arg or "\\" in arg:
        return arg
    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / DEFAULT_BASE_DIR / arg)
