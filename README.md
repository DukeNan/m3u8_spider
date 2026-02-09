# M3U8 下载工具

一个基于 Scrapy 框架的 M3U8 文件下载工具，用于下载 HLS 视频流的所有片段文件。

## 功能特性

- 使用 Scrapy 框架实现高效的并发下载
- 自动解析 M3U8 文件并下载所有 TS 片段
- 默认下载到 `movies/` 目录，合并输出到 `mp4/` 目录
- 提供文件校验脚本，检查下载完整性
- 提供基于 pathlib 的现代化路径处理
- 提供 FFmpeg 合并脚本，将 TS 文件合并为 MP4
- **🆕 MySQL 数据库集成**: 支持从数据库自动读取任务、批量下载、状态管理

## 环境要求

- Python 3.10+
- uv (虚拟环境管理工具)
- ffmpeg (用于合并视频，可选)
- MySQL 5.7+ (用于自动下载功能，可选)

## 安装

1. 激活虚拟环境：
```bash
source .venv/bin/activate
```

2. 安装依赖：
```bash
uv pip install -e .
```

## 使用方法

默认所有下载会保存到项目根目录下的 **`movies/`** 中；合并后的 MP4 默认保存到 **`mp4/`** 目录。校验与合并时，若只传入视频名（如 `my_video`），会自动解析为 `movies/my_video`；传入完整路径或相对路径（如 `./my_video`）则按原路径处理。

### 1. 下载 M3U8 文件

```bash
python main.py <m3u8_url> <filename>
```

参数说明：
- `m3u8_url`: M3U8 文件的 URL 地址
- `filename`: 保存的文件名（将在 `movies/` 下创建同名子目录）

示例：
```bash
python main.py https://example.com/playlist.m3u8 my_video
```
下载完成后文件位于 `movies/my_video/`；日志同时输出到控制台和 `logs/my_video.log`。

可选参数：
- `--concurrent <num>`: 并发下载数（默认: 32）
- `--delay <seconds>`: 下载延迟（秒，默认: 0）

示例：
```bash
python main.py https://example.com/playlist.m3u8 my_video --concurrent 16 --delay 0.1
```

### 2. 校验下载文件

下载完成后，使用校验脚本检查文件是否完整：

```bash
python validate_downloads.py <目录路径或视频名>
```

传入视频名（如 `my_video`）时，默认校验 `movies/my_video`。也可传入完整或相对路径。

示例：
```bash
python validate_downloads.py my_video
```

校验脚本会检查：
- 文件数量是否匹配
- 每个文件的大小
- 是否有空文件

### 3. 合并为 MP4

使用 FFmpeg 将下载的 TS 文件合并为 MP4：

```bash
python merge_to_mp4.py <目录路径或视频名> [output.mp4]
```

传入视频名（如 `my_video`）时，默认从 `movies/my_video` 合并；合成后的 MP4 默认保存到 **`mp4/`** 目录（如 `mp4/my_video.mp4`）。也可传入完整或相对路径。

示例：
```bash
python merge_to_mp4.py my_video
python merge_to_mp4.py my_video output.mp4
```

## 🆕 MySQL 自动下载功能

### 4. 自动化批量下载（从数据库）

本项目支持从 MySQL 数据库自动读取下载任务，实现批量自动化下载。

#### 快速开始

1. **配置数据库连接**

```bash
# 复制配置模板
cp env.example .env

# 编辑配置文件，填写数据库信息
vim .env
```

`.env` 配置示例：
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=video_db
DOWNLOAD_CHECK_INTERVAL=60
```

2. **准备数据库表**

确保数据库中有 `movie_info` 表，包含以下关键字段：
- `id`: 主键
- `number`: 视频编号（用作文件名）
- `m3u8_address`: M3U8 播放列表 URL
- `status`: 下载状态（0=未下载，1=成功，2=失败）
- `m3u8_update_time`: 更新时间

3. **启动自动下载守护进程**

```bash
# 基本启动
python auto_download_daemon.py

# 自定义参数
python auto_download_daemon.py --concurrent 64 --delay 0.5 --check-interval 30
```

参数说明：
- `--concurrent`: 并发下载数（默认: 32）
- `--delay`: 下载延迟（秒，默认: 0）
- `--check-interval`: 检查数据库间隔（秒，默认: 60）

#### 工作流程

```
查询数据库 (status=0)
    ↓
下载视频到 movies/<number>/
    ↓
自动校验完整性
    ↓
更新数据库状态 (status=1或2)
    ↓
循环处理下一个任务
```

#### 状态说明

| status | 含义 | 说明 |
|--------|------|------|
| 0 | 未下载 | 等待处理的任务 |
| 1 | 下载成功 | 下载完整且校验通过 |
| 2 | 下载失败 | 下载失败或校验不通过 |

#### 详细文档

- **[QUICKSTART.md](QUICKSTART.md)**: 5分钟快速入门指南
- **[AUTO_DOWNLOAD_README.md](AUTO_DOWNLOAD_README.md)**: 完整使用手册（500+ 行）
- **[TESTING.md](TESTING.md)**: 详细测试步骤（400+ 行）

## 项目结构

```
m3u8_spider/
├── scrapy_project/          # Scrapy 项目目录
│   ├── scrapy.cfg
│   └── m3u8_spider/         # Scrapy 项目包
│       ├── __init__.py
│       ├── extensions.py    # 扩展（如 M3U8 文件日志）
│       ├── items.py         # 数据项定义
│       ├── logformatter.py  # 自定义日志格式
│       ├── middlewares.py   # 中间件
│       ├── pipelines.py     # 文件保存管道
│       ├── settings.py      # Scrapy 配置
│       └── spiders/         # 爬虫目录
│           ├── __init__.py
│           └── m3u8_downloader.py  # M3U8 下载爬虫
├── main.py                  # 主入口（单个下载）
├── validate_downloads.py    # 校验脚本
├── merge_to_mp4.py         # FFmpeg 合并脚本
├── db_manager.py           # 🆕 数据库管理模块
├── auto_downloader.py      # 🆕 自动下载协调器
├── auto_download_daemon.py # 🆕 守护进程入口
├── env.example             # 🆕 环境变量模板
├── pyproject.toml           # 项目配置与依赖
├── README.md                # 使用说明（本文件）
├── QUICKSTART.md            # 🆕 快速入门指南
├── AUTO_DOWNLOAD_README.md  # 🆕 自动下载完整手册
└── TESTING.md               # 🆕 测试指南
```

## 目录结构

下载和合并过程中会创建以下目录：

```
m3u8_spider/
├── movies/               # 下载的视频片段目录（默认）
│   ├── my_video/         # 每个视频的片段文件
│   │   ├── segment_00000.ts
│   │   ├── segment_00001.ts
│   │   ├── playlist.txt
│   │   ├── content_lengths.json
│   │   └── encryption_info.json  # 若存在加密
│   └── another_video/
├── logs/                 # 下载日志（默认）
│   ├── my_video.log
│   └── another_video.log
└── mp4/                  # 合并后的 MP4 目录（默认）
    ├── my_video.mp4
    └── another_video.mp4
```

## 工作流程

### 单个下载模式

1. **下载阶段**：
   - 解析 M3U8 文件，提取所有 TS 片段 URL
   - 在 `movies/` 下创建目录并保存文件
   - 将 M3U8 内容保存为 `playlist.txt`
   - 并发下载所有 TS 文件到指定目录

2. **校验阶段**：
   - 读取 `playlist.txt` 获取预期文件列表
   - 检查实际下载的文件数量和大小
   - 生成校验报告

3. **合并阶段**：
   - 按顺序读取所有 TS 文件
   - 使用 FFmpeg 合并为单个 MP4 文件
   - 输出到 `mp4/` 目录

### 自动下载模式（MySQL 集成）

1. **初始化**：
   - 加载数据库配置（`.env`）
   - 连接 MySQL 数据库
   - 启动守护进程

2. **主循环**：
   - 查询 `status=0` 的记录
   - 调用下载模块（复用 `main.py`）
   - 自动校验完整性（复用 `validate_downloads.py`）
   - 更新数据库状态和时间戳

3. **优雅退出**：
   - 捕获 Ctrl+C 信号
   - 完成当前任务
   - 打印统计信息
   - 关闭数据库连接

## 注意事项

- 确保有足够的磁盘空间存储所有 TS 文件
- 合并 MP4 需要安装 FFmpeg
- 下载速度取决于网络状况和服务器限制
- 如果下载中断，可以重新运行下载命令（会覆盖已存在的文件）

## 故障排除

### 下载失败
- 检查网络连接
- 验证 M3U8 URL 是否可访问
- 尝试降低并发数（`--concurrent`）

### 合并失败
- 确保已安装 FFmpeg：`ffmpeg -version`
- 检查所有 TS 文件是否完整下载
- 运行校验脚本确认文件完整性

### 文件数量不匹配
- 检查网络连接是否稳定
- 查看 Scrapy 日志了解失败原因
- 重新运行下载命令

### 数据库连接失败（自动下载模式）
- 检查 `.env` 文件配置是否正确
- 确认 MySQL 服务正在运行
- 验证数据库用户名和密码
- 检查防火墙设置

### 自动下载任务未执行
- 确认数据库中有 `status=0` 的记录
- 检查 `m3u8_address` 字段不为空
- 查看守护进程日志输出
- 验证数据库表结构是否正确

## 相关文档

- **[QUICKSTART.md](QUICKSTART.md)**: 5分钟快速入门（MySQL 自动下载）
- **[AUTO_DOWNLOAD_README.md](AUTO_DOWNLOAD_README.md)**: 完整使用手册（MySQL 集成）
- **[TESTING.md](TESTING.md)**: 详细测试步骤和验证清单
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**: 技术实现总结

## 许可证

MIT License
