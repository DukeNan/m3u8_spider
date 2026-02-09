#!/usr/bin/env python3
"""
语法检查脚本 - 不执行导入，只检查语法
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

print("=" * 60)
print("🔍 Python 语法检查")
print("=" * 60)

errors = []


def check_syntax(filepath: Path) -> bool:
    """检查 Python 文件语法"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code)
        return True
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


# 要检查的文件
files_to_check = [
    "db_manager.py",
    "auto_downloader.py",
    "auto_download_daemon.py",
    "verify_integration.py",
]

project_root = Path(__file__).parent

for filename in files_to_check:
    filepath = project_root / filename
    print(f"\n📄 检查 {filename}...")

    if not filepath.exists():
        print("   ❌ 文件不存在")
        errors.append((filename, "文件不存在"))
        continue

    result = check_syntax(filepath)
    if result is True:
        print("   ✅ 语法正确")
    else:
        print(f"   ❌ 语法错误: {result[1]}")
        errors.append((filename, result[1]))

# 检查配置文件
print("\n📄 检查配置文件...")
config_files = ["env.example", "AUTO_DOWNLOAD_README.md", "TESTING.md"]
for filename in config_files:
    filepath = project_root / filename
    if filepath.exists():
        print(f"   ✅ {filename} 存在")
    else:
        print(f"   ⚠️  {filename} 不存在")

# 总结
print("\n" + "=" * 60)
if errors:
    print(f"❌ 检查失败: 发现 {len(errors)} 个错误")
    print("=" * 60)
    for file, error in errors:
        print(f"\n{file}:")
        print(f"  {error}")
    sys.exit(1)
else:
    print("✅ 检查通过: 所有 Python 文件语法正确")
    print("=" * 60)
    print("\n📝 集成完成！")
    print("\n下一步操作:")
    print("1. 安装依赖:")
    print("   source .venv/bin/activate")
    print("   uv pip install -e .")
    print("\n2. 配置数据库:")
    print("   cp env.example .env")
    print("   vim .env  # 编辑数据库配置")
    print("\n3. 测试连接:")
    print("   python verify_integration.py")
    print("\n4. 启动守护进程:")
    print("   python auto_download_daemon.py")
    print("\n📖 文档:")
    print("- AUTO_DOWNLOAD_README.md: 完整使用指南")
    print("- TESTING.md: 详细测试步骤")
    sys.exit(0)
