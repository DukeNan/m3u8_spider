# Codebase Concerns

**Analysis Date:** 2026-03-29

## Summary

项目整体质量中等，代码组织清晰，有良好的模块化设计。但存在几个关键问题：**完全缺乏测试**、**多处静默异常处理**、**数据库连接池缺失**、以及**Python 版本要求过高**。这些问题需要优先处理以确保代码可维护性和生产稳定性。

---

## Testing

### Missing Test Coverage
- **Location**: 整个项目 (`m3u8_spider/`, `cli/`, `scrapy_project/`)
- **Severity**: High
- **Description**: 项目完全没有单元测试。所有 `*test*.py` 文件都位于 `.venv/` 依赖包中，而非项目源码。
- **Impact**:
  - 无法验证重构是否破坏功能
  - 回归问题难以早期发现
  - 对守护进程等长期运行组件的行为无保障
- **Recommendation**:
  1. 优先为 `m3u8_spider/core/validator.py`、`m3u8_spider/core/recovery.py` 添加单元测试
  2. 为 `m3u8_spider/database/manager.py` 的数据库操作添加集成测试
  3. 使用 pytest + pytest-mock，配置覆盖率目标 >= 70%

---

## Error Handling

### Silent Exception Swallowing
- **Location**:
  - `m3u8_spider/core/recovery.py:156` - `_load_encryption_info()`
  - `m3u8_spider/core/validator.py:170` - `ContentLengthLoader.load()`
  - `m3u8_spider/core/validator.py:212` - `_validate_content_length()`
  - `scrapy_project/m3u8_spider/pipelines.py:56` - `open_spider()` 加载 content_lengths
  - `scrapy_project/m3u8_spider/pipelines.py:133` - `media_downloaded()` 解析 Content-Length
  - `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py:288` - `_decode_b64_url()`
  - `m3u8_spider/utils/merger.py:73` - `EncryptionInfo.from_directory()`
- **Severity**: Medium
- **Description**: 多处使用 `except Exception:` 捕获异常后静默返回空值/None，不记录错误日志。这掩盖了潜在问题。
- **Impact**:
  - JSON 解析失败、文件读取失败等错误无法追踪
  - 下载校验失败原因不可见
  - 调试困难
- **Recommendation**:
  ```python
  # 改为记录异常原因
  except Exception as e:
      logger.warning(f"加载 encryption_info.json 失败: {e}")
      return {}
  ```

### Broad Exception Catch in Daemon Loop
- **Location**: `m3u8_spider/automation/auto_downloader.py:135`, `m3u8_spider/automation/m3u8_refresher.py:123`
- **Severity**: Medium
- **Description**: 守护进程主循环使用 `except Exception as e` 捕获所有异常，仅打印 traceback 后继续运行。
- **Impact**: 某些不可恢复错误（如数据库连接彻底失效）可能导致无限循环重试。
- **Recommendation**: 区分可恢复与不可恢复异常，对关键错误（连接失败）增加重试上限后退出。

### Subprocess Error Handling
- **Location**: `m3u8_spider/core/downloader.py:160-167`
- **Severity**: Medium
- **Description**: 使用 `subprocess.run(..., check=True)`，当 scrapy 命令失败时直接抛出 `CalledProcessError`，调用方未处理。
- **Impact**: 下载失败会导致整个程序崩溃，而非返回错误码。批量下载时单个任务失败会导致守护进程退出。
- **Recommendation**: 捕获 `CalledProcessError`，返回成功/失败状态而非抛出异常。

---

## Database

### Single Connection Instead of Pool
- **Location**: `m3u8_spider/database/manager.py:88-89`
- **Severity**: Medium
- **Description**: `DatabaseManager` 使用单个 `pymysql.Connection`，而非连接池。守护进程长期运行可能导致连接超时或失效。
- **Impact**:
  - 连接断开后重连有延迟
  - 无法并发处理多个数据库操作
  - MySQL 服务器端连接资源未优化
- **Recommendation**: 使用 `DBUtils` 或自定义连接池，或考虑切换到 SQLAlchemy 连接池。

### Missing Row Locking
- **Location**: `m3u8_spider/database/manager.py:159-167` - `get_pending_tasks()`
- **Severity**: Medium
- **Description**: 查询待处理任务时未使用 `SELECT ... FOR UPDATE` 锁定行。多守护进程实例可能同时处理同一任务。
- **Impact**: 重复下载、资源浪费、状态冲突。
- **Recommendation**:
  1. 添加行锁定 `SELECT ... FOR UPDATE SKIP LOCKED`
  2. 或使用状态字段乐观锁（查询时同时更新状态为 "processing"）

### Database Connection Info Logged
- **Location**: `m3u8_spider/database/manager.py:100-102`
- **Severity**: Low
- **Description**: 连接成功时打印完整连接信息（host:port/database）。
- **Impact**: 日志泄露基础设施信息，敏感环境需注意。
- **Recommendation**: 仅打印 host，不打印完整连接串。

---

## Configuration & Dependencies

### Python Version Requirement Too High
- **Location**: `pyproject.toml:14`
- **Severity**: High
- **Description**: `requires-python = ">=3.14"` 要求 Python 3.14，但 Python 3.14 尚未正式发布（当前最新稳定版为 3.13）。
- **Impact**: 用户无法在标准 Python 环境中安装此包。
- **Recommendation**: 改为 `requires-python = ">=3.12"` 或 `>=3.13`。

### Dependency Version Not Locked
- **Location**: `pyproject.toml:15-23`
- **Severity**: Medium
- **Description**: `scrapy>=2.11.0` 使用 `>=` 而非固定版本。依赖升级可能引入不兼容变更。
- **Impact**: 不同环境安装可能得到不同版本，行为不一致。
- **Recommendation**: `uv.lock` 文件已存在，确保部署时使用锁定版本。

### Deprecated utils Cache Files
- **Location**: `utils/__pycache__/`
- **Severity**: Low
- **Description**: 存在废弃模块的编译缓存文件：`db_manager.cpython-*.pyc`、`scrapy_manager.cpython-*.pyc`、`auto_downloader.cpython-*.pyc`、`recovery_downloader.cpython-*.pyc`、`logger.cpython-*.pyc`。这些模块已迁移到 `m3u8_spider/` 包内。
- **Impact**: 可能造成混淆，导入错误时可能加载旧代码。
- **Recommendation**: 删除 `utils/__pycache__/` 目录，考虑删除整个 `utils/` 目录（仅包含缓存）。

---

## Security & Compliance

### robots.txt Compliance Disabled
- **Location**: `scrapy_project/m3u8_spider/settings.py:16`
- **Severity**: Medium
- **Description**: `ROBOTSTXT_OBEY = False` 明确禁用 robots.txt 规则遵守。
- **Impact**: 爬虫可能违反网站爬取政策，增加被封禁风险，法律合规风险。
- **Recommendation**: 评估目标网站 robots.txt，对允许的内容启用遵守，或添加免责声明。

### Hardcoded User-Agent
- **Location**: `scrapy_project/m3u8_spider/settings.py:39`
- **Severity**: Low
- **Description**: 固定 Chrome 120 User-Agent，随时间推移会显得过时。
- **Impact**: 可能被目标网站识别为异常客户端。
- **Recommendation**: 使用随机 User-Agent 或定期更新版本号。

### Hardcoded Remote Path
- **Location**: `cli/sync_mp4.sh:10`
- **Severity**: Low
- **Description**: 远程路径 `/share/data/jellyfin/media/jable` 硬编码。
- **Impact**: 不同环境需修改脚本。
- **Recommendation**: 改为环境变量 `REMOTE_PATH`，与 `REMOTE_HOST` 保持一致风格。

### Database Password in .env File
- **Location**: `.env` 文件
- **Severity**: Low
- **Description**: MySQL 密码存储在 `.env` 文件中（明文）。
- **Impact**: 仅本地开发使用，风险有限。生产环境需注意。
- **Recommendation**: 生产环境使用环境变量或密钥管理服务，`.env` 文件不提交到 git（已在 `.gitignore`）。

---

## Performance & Scalability

### Subprocess Without Timeout
- **Location**: `m3u8_spider/core/downloader.py:160` - `subprocess.run(cmd, ...)`
- **Severity**: Medium
- **Description**: 调用 Scrapy 时无超时设置。若目标服务器响应极慢或网络异常，下载可能无限挂起。
- **Impact**: 守护进程任务积压，资源无法释放。
- **Recommendation**: 添加 `timeout` 参数（如 3600 秒），并处理超时异常。

### No Index Mentioned for Query Fields
- **Location**: `m3u8_spider/database/manager.py` - SQL 查询 `WHERE status = 0`, `ORDER BY id ASC`
- **Severity**: Medium
- **Description**: 数据库表 `movie_info` 的查询依赖 `status` 和 `id` 字段，但无文档说明索引存在。
- **Impact**: 大数据量时查询性能下降。
- **Recommendation**:
  1. 确认表有 `INDEX(status, id)`
  2. 在文档中说明数据库 schema 要求

### Browser Automation for M3U8 Refresh
- **Location**: `m3u8_spider/core/m3u8_fetcher.py:41-62`
- **Severity**: Medium
- **Description**: M3U8 URL 刷新使用 `crawl4ai`（浏览器自动化），相比简单 HTTP 请求开销大得多。
- **Impact**:
  - 资源消耗高（启动浏览器实例）
  - 目标网站可能检测并封禁自动化行为
  - 刷新批次大时可能触发反爬
- **Recommendation**:
  1. 优先尝试简单 HTTP + 正则解析
  2. 浏览器自动化作为备选方案
  3. 控制并发刷新数量

---

## Code Quality

### Inconsistent Return Types
- **Location**: 多个函数返回 `None | dict` 或 `None | object` 混合类型
- **Severity**: Low
- **Description**: 如 `_load_encryption_info()` 正常返回 dict，异常返回空 dict，而非 Optional。数据库操作失败返回 `False` 或空列表，校验失败返回 `(False, {})` 元组，合并失败直接 `sys.exit(1)`。
- **Impact**: 调用方需要针对每个模块做不同处理，增加复杂度。
- **Recommendation**: 统一返回 Result 类型或使用明确的异常类型。

### URL Parsing Edge Cases
- **Location**: `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py:86-117` - `UrlResolver`
- **Severity**: Medium
- **Description**: `UrlResolver` 处理非标准 M3U8 结构时可能失败。
- **Impact**: 某些 CDN 的 M3U8 文件无法正确解析，特定视频源可能下载失败。
- **Recommendation**: 添加更多解析场景的测试用例。

### Encryption IV Format Conversion Missing
- **Location**: `m3u8_spider/utils/merger.py:73-80`
- **Severity**: Medium
- **Description**: `encryption_info.json` 存储的 IV 是 `0x...` 格式，但 FFmpeg 需要纯十六进制字符串。
- **Impact**: 加密视频合并可能失败。
- **Recommendation**: 添加 IV 格式转换逻辑。

---

## Graceful Shutdown

### No In-Progress Download Tracking
- **Location**: `m3u8_spider/automation/auto_downloader.py:113-122` - 信号处理
- **Severity**: Medium
- **Description**: 收到 SIGINT 后设置 `_running = False`，但正在进行的 subprocess 下载不被追踪。
- **Impact**:
  - 下载可能被中断但数据库状态未更新
  - 下次启动需恢复流程重新处理
- **Recommendation**:
  1. 记录当前处理任务 ID 到文件
  2. 退出前等待当前下载完成或标记为中断状态

---

## Temporary File Cleanup

### Temp Files May Remain in Edge Cases
- **Location**: `m3u8_spider/utils/merger.py:372-376`
- **Severity**: Low
- **Description**: 如果合并成功但 `_print_success` 失败，临时文件可能残留。
- **Impact**: 磁盘空间浪费，影响有限。
- **Recommendation**: 使用 `try/finally` 确保清理。

---

## Configuration Loading

### Hardcoded Path Assumption
- **Location**: `m3u8_spider/config.py:23`
- **Severity**: Low
- **Description**: `_env_path = Path(__file__).resolve().parent.parent.parent / ".env"` 假设 .env 在项目根目录。
- **Impact**: 从非标准位置调用时无法加载配置。当前使用方式能工作。
- **Recommendation**: 支持环境变量 `M3U8_SPIDER_ENV` 指定配置路径。

---

## Priority Ranking

| 优先级 | 问题 | 紧急程度 | 工作量 |
|--------|------|----------|--------|
| 1 | Python 版本要求过高 (`>=3.14`) | High | Low |
| 2 | 缺乏测试覆盖 | High | High |
| 3 | 静默异常处理 | Medium | Medium |
| 4 | 数据库连接池缺失 | Medium | Medium |
| 5 | 数据库行锁定缺失 | Medium | Medium |
| 6 | Subprocess 无超时 | Medium | Low |
| 7 | robots.txt 禁用 | Medium | Low |
| 8 | 加密 IV 格式转换缺失 | Medium | Low |
| 9 | URL 解析边界情况 | Medium | Medium |
| 10 | 废弃缓存文件 | Low | Low |
| 11 | 硬编码配置 | Low | Low |
| 12 | 其他代码质量问题 | Low | Medium |

---

*Concerns audit: 2026-03-29*