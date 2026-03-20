# Codebase Concerns

**Analysis Date:** 2026-03-20

## 测试覆盖缺失

**问题:** 整个项目没有任何测试文件

- 文件: 无测试文件
- 影响: 任何代码更改都可能引入 bug，且无法快速验证修复
- 风险: 高 - 核心功能（下载、校验、恢复、合并）均无测试保护
- 建议: 至少为核心模块添加单元测试

---

## Subprocess 错误处理

**下载器调用失败时崩溃**

- 文件: `m3u8_spider/core/downloader.py` (第 160-167 行)
- 问题: 使用 `subprocess.run(..., check=True)`，当 scrapy 命令失败时直接抛出 `CalledProcessError`，调用方未处理
- 影响: 下载失败会导致整个程序崩溃，而非返回错误码
- 风险: 中 - 批量下载时单个任务失败会导致守护进程退出

```python
# 当前代码
subprocess.run(cmd, cwd=str(config.scrapy_project_dir), check=True, capture_output=False)
```

- 建议: 捕获 `CalledProcessError`，返回成功/失败状态而非抛出异常

---

## 数据库连接管理

**每次操作复用单一连接，无连接池**

- 文件: `m3u8_spider/database/manager.py` (第 88 行)
- 问题: `self._connection` 是单一连接对象，无连接池。高并发场景下性能受限
- 影响: 长时间运行时连接可能因 MySQL 超时而断开
- 风险: 中 - 生产环境守护进程需要更强的连接管理

- 建议: 使用 `pymysql` 的连接池或 SQLAlchemy

---

## 加密 IV 格式转换缺失

**FFmpeg 无法识别存储的 IV 格式**

- 文件: `m3u8_spider/utils/merger.py` (第 73-80 行)
- 问题: `encryption_info.json` 存储的 IV 是 `0x...` 格式，但 FFmpeg 需要纯十六进制字符串
- 影响: 加密视频合并可能失败
- 风险: 中 - 所有加密视频无法正确合并

- 建议: 添加 IV 格式转换逻辑

---

## 恢复流程异常处理

**元数据下载失败时未清理状态**

- 文件: `m3u8_spider/core/recovery.py` (第 56-68 行)
- 问题: 如果元数据下载 (`metadata_only=True`) 失败，流程中断但未报告具体错误
- 影响: 用户不知道是网络问题还是 M3U8 解析问题
- 风险: 中 - 问题排查困难

- 建议: 捕获异常并记录详细的失败原因

---

## 配置文件加载路径

**硬编码路径假设项目结构**

- 文件: `m3u8_spider/config.py` (第 23 行)
- 问题: `_env_path = Path(__file__).resolve().parent.parent.parent / ".env"` 假设 .env 在项目根目录
- 影响: 从非标准位置调用时无法加载配置
- 风险: 低 - 当前使用方式能工作

- 建议: 支持环境变量 `M3U8_SPIDER_ENV` 指定配置路径

---

## 日志配置不一致

**混用自定义 logger 和 print**

- 文件: 多处
- 问题: CLI 入口使用 `print()`，核心模块使用自定义 logger
- 影响: 无法通过统一配置控制日志输出
- 风险: 低 - 不影响功能，但影响排查

- 建议: 统一使用 logger，移除 print 语句

---

## 临时文件清理

**特定情况下临时文件未删除**

- 文件: `m3u8_spider/utils/merger.py` (第 372-376 行)
- 问题: 如果合并成功但 `_print_success` 失败，临时文件可能残留
- 影响: 磁盘空间浪费
- 风险: 低 - 影响有限

- 建议: 使用 `try/finally` 确保清理

---

## 错误处理模式不统一

**模块间返回值的语义不一致**

- 文件: `database/manager.py`, `core/validator.py`, `utils/merger.py`
- 问题: 
  - 数据库操作失败返回 `False` 或空列表
  - 校验失败返回 `(False, {})` 元组
  - 合并失败直接 `sys.exit(1)`
- 影响: 调用方需要针对每个模块做不同处理
- 风险: 中 - 增加调用方复杂度

- 建议: 统一返回 Result 类型或异常类型

---

## URL 解析边界情况

**相对路径解析可能出错**

- 文件: `scrapy_project/m3u8_spider/spiders/m3u8_downloader.py` (第 86-117 行)
- 问题: `UrlResolver` 处理非标准 M3U8 结构时可能失败
- 影响: 某些 CDN 的 M3U8 文件无法正确解析
- 风险: 中 - 特定视频源可能下载失败

- 建议: 添加更多解析场景的测试用例

---

## 安全考虑

**数据库密码明文存储**

- 文件: `.env` 文件
- 问题: MySQL 密码存储在 `.env` 文件中
- 风险: 低 - 仅本地开发使用

- 建议: 生产环境使用环境变量或密钥管理服务

---

## 依赖版本风险

**未锁定关键依赖版本**

- 文件: `pyproject.toml` (第 15-23 行)
- 问题: `scrapy>=2.11.0` 使用 `>=` 而非固定版本
- 影响: 依赖升级可能引入不兼容变更
- 风险: 中

- 建议: 使用 `uv lock` 锁定版本，或使用精确版本号

---

*Concerns audit: 2026-03-20*
