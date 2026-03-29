# External Integrations

**Analysis Date:** 2026-03-29

## APIs & External Services

**M3U8/HLS 视频源:**
- HTTP M3U8 播放列表 URL - 通过 Scrapy spider 请求
  - SDK/Client: Scrapy 内置 HTTP 下载器 + `m3u8` 库解析
  - 配置: 通过 CLI 参数传入 URL
  - 文件: `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py`

**网页爬取（可选）:**
- crawl4ai + Playwright - 用于 M3U8 URL 刷新守护进程
  - SDK/Client: `crawl4ai.AsyncWebCrawler`
  - 配置: 可选依赖，需 `pip install crawl4ai && playwright install`
  - 文件: `m3u8_spider/core/m3u8_fetcher.py`

## Data Storage

**Databases:**
- MySQL - 批量下载任务队列
  - 连接: 环境变量 `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
  - Client: `pymysql`（见 `m3u8_spider/database/manager.py`）
  - 表结构: `movie_info` 表，必需字段包括 `id`, `number`, `m3u8_address`, `status`, `m3u8_update_time`
  - 状态值: `status` 字段（0=待处理, 1=成功, 2=失败）

- PostgreSQL（可选）:
  - 可通过 `psycopg2-binary` 支持
  - 配置: 需额外实现连接逻辑

**File Storage:**
- 本地文件系统
  - `movies/<name>/` - 下载的 TS 片段目录
  - `mp4/` - 合并后的 MP4 文件
  - `logs/<name>.log` - 每次下载的日志文件

**Caching:**
- 无显式缓存层
- Scrapy HTTP Cache 可启用（见 `settings.py` 第 79-85 行，默认禁用）

## Authentication & Identity

**Auth Provider:**
- 无内置认证系统
- 外部视频源可能需要特定 headers（见 `settings.py` 第 36-40 行 `DEFAULT_REQUEST_HEADERS`）

## Monitoring & Observability

**Error Tracking:**
- 无专门错误追踪服务
- 日志文件记录: `logs/<name>.log`

**Logs:**
- Python `logging` 模块
- 配置: `m3u8_spider/logger.py`
- 格式: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- 双输出: 控制台 + 文件（通过 Scrapy 扩展 `M3U8FileLogExtension`）

**Progress:**
- `tqdm` 进度条 - 用于守护进程冷却倒计时（见 `auto_downloader.py`）

## CI/CD & Deployment

**Hosting:**
- 本地运行为主
- 可部署到任意 Python 环境

**CI Pipeline:**
- 无 CI 配置文件

**Remote Sync:**
- rsync 同步到 Jellyfin 媒体服务器
  - 脚本: `cli/sync_mp4.sh`
  - 目标: 远程路径 `/share/data/jellyfin/media/jable`
  - 用法: `./cli/sync_mp4.sh user@host`

## Environment Configuration

**Required env vars:**
- `MYSQL_HOST` - MySQL 主机地址
- `MYSQL_PORT` - MySQL 端口（默认 3306）
- `MYSQL_USER` - MySQL 用户名
- `MYSQL_PASSWORD` - MySQL 密码
- `MYSQL_DATABASE` - MySQL 数据库名

**Optional env vars:**
- `DEFAULT_CONCURRENT` - 默认并发数（默认 32）
- `DEFAULT_DELAY` - 默认下载延迟秒数（默认 0）
- `DOWNLOAD_COOLDOWN_SECONDS` - 下载后冷却时间（默认 30）
- `DOWNLOAD_CHECK_INTERVAL` - 守护进程检查间隔（默认 60）
- `M3U8_REFRESH_INTERVAL` - M3U8 刷新检查间隔（默认 300）
- `M3U8_REFRESH_MIN_MINUTES` - M3U8 刷新最小间隔分钟（默认 10）
- `LOG_LEVEL` - 日志级别（默认 INFO）

**Secrets location:**
- `.env` 文件（项目根目录）
- 模板参考 `env.example`

**Config module:**
- `m3u8_spider/config.py` - 统一配置加载与默认值定义

## Webhooks & Callbacks

**Incoming:**
- 无

**Outgoing:**
- 无

## External Tools

**FFmpeg:**
- 用于 TS 文件合并为 MP4
- 检查: `utils/merger.py` 第 88-101 行 `FFmpegChecker.is_available()`
- 安装提示:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: 从 https://ffmpeg.org/download.html 下载

**Playwright（可选）:**
- 用于 M3U8 URL 刷新功能的浏览器自动化
- 需额外安装: `playwright install`

---

*Integration audit: 2026-03-29*