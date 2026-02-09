#!/usr/bin/env python3
"""
快速验证脚本 - 检查代码语法和基本导入
"""

from __future__ import annotations

import sys
from pathlib import Path

print("=" * 60)
print("🔍 代码验证检查")
print("=" * 60)

errors = []

# 测试 1: 检查 db_manager.py
print("\n1️⃣ 检查 db_manager.py...")
try:
    import db_manager

    print("   ✅ 导入成功")
    print(f"   - DatabaseManager: {hasattr(db_manager, 'DatabaseManager')}")
    print(f"   - DownloadTask: {hasattr(db_manager, 'DownloadTask')}")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    errors.append(("db_manager.py", str(e)))

# 测试 2: 检查 auto_downloader.py
print("\n2️⃣ 检查 auto_downloader.py...")
try:
    import auto_downloader

    print("   ✅ 导入成功")
    print(f"   - AutoDownloader: {hasattr(auto_downloader, 'AutoDownloader')}")
    print(f"   - AutoDownloadConfig: {hasattr(auto_downloader, 'AutoDownloadConfig')}")
    print(
        f"   - create_auto_downloader: {hasattr(auto_downloader, 'create_auto_downloader')}"
    )
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    errors.append(("auto_downloader.py", str(e)))

# 测试 3: 检查 auto_download_daemon.py
print("\n3️⃣ 检查 auto_download_daemon.py...")
try:
    import auto_download_daemon

    print("   ✅ 导入成功")
    print(
        f"   - load_config_from_env: {hasattr(auto_download_daemon, 'load_config_from_env')}"
    )
    print(f"   - parse_args: {hasattr(auto_download_daemon, 'parse_args')}")
    print(f"   - main: {hasattr(auto_download_daemon, 'main')}")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    errors.append(("auto_download_daemon.py", str(e)))

# 测试 4: 检查现有模块兼容性
print("\n4️⃣ 检查现有模块兼容性...")
try:
    import main

    print("   ✅ main.py 导入成功")
    print(f"   - DownloadConfig: {hasattr(main, 'DownloadConfig')}")
    print(f"   - _run_scrapy: {hasattr(main, '_run_scrapy')}")
except Exception as e:
    print(f"   ❌ main.py 导入失败: {e}")
    errors.append(("main.py", str(e)))

try:
    import validate_downloads

    print("   ✅ validate_downloads.py 导入成功")
    print(
        f"   - validate_downloads: {hasattr(validate_downloads, 'validate_downloads')}"
    )
except Exception as e:
    print(f"   ❌ validate_downloads.py 导入失败: {e}")
    errors.append(("validate_downloads.py", str(e)))

# 测试 5: 检查文件存在性
print("\n5️⃣ 检查配置文件...")
project_root = Path(__file__).parent
env_example = project_root / "env.example"
if env_example.exists():
    print("   ✅ env.example 存在")
else:
    print("   ❌ env.example 不存在")
    errors.append(("env.example", "文件不存在"))

readme = project_root / "AUTO_DOWNLOAD_README.md"
if readme.exists():
    print("   ✅ AUTO_DOWNLOAD_README.md 存在")
else:
    print("   ⚠️  AUTO_DOWNLOAD_README.md 不存在（可选）")

testing = project_root / "TESTING.md"
if testing.exists():
    print("   ✅ TESTING.md 存在")
else:
    print("   ⚠️  TESTING.md 不存在（可选）")

# 总结
print("\n" + "=" * 60)
if errors:
    print(f"❌ 验证失败: 发现 {len(errors)} 个错误")
    print("=" * 60)
    for file, error in errors:
        print(f"\n{file}:")
        print(f"  {error}")
    sys.exit(1)
else:
    print("✅ 验证通过: 所有检查均通过")
    print("=" * 60)
    print("\n📝 下一步:")
    print("1. 安装依赖: uv pip install -e .")
    print("2. 配置数据库: cp env.example .env && vim .env")
    print("3. 启动守护进程: python auto_download_daemon.py")
    print("\n📖 查看文档:")
    print("- AUTO_DOWNLOAD_README.md: 使用指南")
    print("- TESTING.md: 测试指南")
    sys.exit(0)
