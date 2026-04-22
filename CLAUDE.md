# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Python M3U8 视频下载器，基于 Scrapy 框架。支持两种模式：
- **手动下载**: `m3u8-download <url> <filename>`
- **自动批处理**: MySQL 数据库集成，守护进程模式

恢复流程: 填充元数据 → 验证 → 重试失败片段 (最多 3 轮)

## 开发命令

```bash
# 安装
uv pip install -e .

# 代码检查
ruff check .

# 格式化和修复
ruff format .

# 运行守护进程
make daemon

# 批量合并
make batch-merge
make batch-merge-dry  # 预览模式
```

## 目录结构

- `movies/<name>/` - 下载的 TS 片段
- `mp4/` - 合并后的 MP4 文件
- `logs/<name>.log` - 下载日志

## 核心命令

```bash
# 下载
m3u8-download <m3u8_url> <filename> [--concurrent 32] [--delay 0]

# 验证
python -m m3u8_spider.core.validator <video_name>

# 合并
python -m m3u8_spider.utils.merger <video_name> [output.mp4]

# 批量合并
m3u8-batch-merge [--dry-run] [--no-delete]

# 同步到 Jellyfin
./cli/sync_mp4.sh user@host

# 守护进程 (MySQL)
m3u8-daemon [--concurrent 32] [--delay 0] [--check-interval 60] [--cooldown 300]

# M3U8 URL 刷新守护进程（检测旧视频是否有新地址）
m3u8-refresh
```

## 代码风格

- 使用 `pathlib.Path` 替代 `os.path`
- 添加 `from __future__ import annotations`
- 类型提示使用 `list[str] | None` 风格
- 优先使用模块级函数而非类

## 架构

### Scrapy 三种运行模式

Spider 通过 `metadata_only` 和 `retry_urls` 两个互斥参数切换模式：

| 模式 | metadata_only | retry_urls | 用途 |
|------|---------------|------------|------|
| 完整下载 | False | None | 首次下载所有 TS 片段 |
| 元数据补齐 | True | None | 仅下载 playlist.txt、encryption_info.json、密钥文件 |
| 失败重试 | False | `[{"url":..., "filename":...}]` | 仅重试指定 URL |

### 核心入口

| 文件 | 用途 |
|------|------|
| `cli/main.py` | 单次下载入口 |
| `cli/daemon.py` | 守护进程入口 |
| `m3u8_spider/core/downloader.py` | `DownloadConfig` + `run_scrapy()`（通过 subprocess 调用 Scrapy） |
| `m3u8_spider/core/recovery.py` | 恢复流程协调器 |
| `m3u8_spider/core/m3u8_fetcher.py` | M3U8 文件获取与解析 |
| `m3u8_spider/core/validator.py` | 下载验证 |
| `m3u8_spider/utils/merger.py` | FFmpeg 合并 |
| `m3u8_spider/automation/auto_downloader.py` | 自动下载协调器 |
| `m3u8_spider/automation/m3u8_refresher.py` | M3U8 URL 刷新检测 |
| `m3u8_spider/database/manager.py` | MySQL 操作 |

### Scrapy 项目

位于 `scrapy_project/m3u8_spider/`:
- `spiders/m3u8_downloader.py` - 核心 spider（三模式逻辑）
- `pipelines.py` - 文件下载 pipeline
- `settings.py` - Scrapy 配置（32 并发、AutoThrottle）

## 测试

项目目前无测试套件。

## MySQL 集成

数据库表 `movie_info` 必需字段:
- `id`, `number` (文件名), `m3u8_address`, `status` (0=待处理, 1=成功, 2=失败), `m3u8_update_time`

配置文件 `.env` 参考 `env.example`，完整选项见 `m3u8_spider/config.py`。

## 注意事项

- Scrapy 通过 subprocess 执行，运行目录为 `scrapy_project/`
- 使用 `pathlib.Path` 处理所有文件操作
- `metadata_only` 和 `retry_urls` 互斥
- 守护进程每个下载独立 subprocess，避免 reactor 冲突