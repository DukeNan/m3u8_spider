# External Integrations

**Analysis Date:** 2026-03-20

## APIs & External Services

**M3U8 视频源:**
- 任意提供 M3U8 播放列表的视频网站
- 通过 Scrapy spider 下载 TS 片段
- 支持相对/绝对 URL 自动解析
- 支持 AES-128 加密视频

**页面爬取 (可选):**
- crawl4ai - 用于从页面 HTML 中提取 M3U8 URL
- 异步浏览器爬取，支持 JavaScript 渲染页面
- 仅 `m3u8-refresh` 守护进程需要

## Data Storage

**MySQL 数据库:**
- 数据库类型: MySQL
- 驱动: PyMySQL
- 用途: 存储下载任务队列 (`movie_info` 表)
- 连接配置: 通过 `.env` 文件配置
  - `MYSQL_HOST`
  - `MYSQL_PORT`
  - `MYSQL_USER`
  - `MYSQL_PASSWORD`
  - `MYSQL_DATABASE`
- 配置位置: `m3u8_spider/config.py`
- 管理模块: `m3u8_spider/database/manager.py`

**PostgreSQL (可选):**
- 驱动: psycopg2-binary (可选依赖)
- 迁移工具: `m3u8_spider/utils/migration.py`
- 支持从 SQLite 迁移到 PostgreSQL

**SQLite (迁移源):**
- 用于从 SQLite 数据库迁移数据到 MySQL/PostgreSQL

**文件存储:**
- 本地文件系统存储
- 下载目录: `movies/<name>/` - TS 片段
- 输出目录: `mp4/` - 合并后的 MP4 文件
- 日志目录: `logs/` - 下载日志

**No 缓存系统:**
- 项目不使用 Redis 或其他缓存

## Authentication & Identity

**无内置认证系统:**
- 不需要用户认证
- 数据库使用 MySQL 用户权限控制

## Monitoring & Observability

**日志系统:**
- Python `logging` 模块
- 自定义配置: `m3u8_spider/logger.py`
- 支持控制台 + 文件双重输出
- 日志文件: `logs/<name>.log`
- 格式: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**无外部监控服务:**
- 不使用 Sentry, Datadog 等

## CI/CD & Deployment

**部署方式:**
- 手动安装部署
- 通过 `uv pip install -e .` 安装

**无 CI/CD 管道:**
- 不使用 GitHub Actions, GitLab CI 等
- 无自动化测试/部署

**远程同步:**
- rsync - 通过 `cli/sync_mp4.sh` 同步 MP4 到 Jellyfin
- 目标路径: `/share/data/jellyfin/media/jable`

**守护进程管理:**
- 通过命令行参数管理
- 无 systemd/supervisor 集成

## Environment Configuration

**必需的环境变量 (MySQL):**
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=video_db
```

**可选环境变量:**
```
DOWNLOAD_CHECK_INTERVAL=60      # 下载检查间隔 (秒)
DEFAULT_CONCURRENT=32           # 默认并发数
DEFAULT_DELAY=0                  # 请求延迟
DOWNLOAD_COOLDOWN_SECONDS=30     # 冷却时间
LOG_LEVEL=INFO                   # 日志级别
M3U8_REFRESH_INTERVAL=300       # M3U8 刷新间隔 (秒)
M3U8_REFRESH_MIN_MINUTES=10     # 刷新最小间隔 (分钟)
```

**配置文件位置:**
- 主配置: `m3u8_spider/config.py`
- 环境模板: `env.example`
- 实际环境变量: `.env` (不提交到 git)

## Webhooks & Callbacks

**无 webhook 系统:**
- 不需要接收外部回调
- 视频下载完全由守护进程主动查询数据库驱动

## Database Schema

**表: `movie_info`**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| number | VARCHAR | 文件名 |
| m3u8_address | VARCHAR | M3U8 URL |
| status | INT | 0=待处理, 1=成功, 2=失败 |
| title | VARCHAR | 标题 (可选) |
| provider | VARCHAR | 来源 (可选) |
| url | VARCHAR | 页面 URL (用于刷新) |
| m3u8_update_time | DATETIME | M3U8 更新时间 |

---

*Integration audit: 2026-03-20*
