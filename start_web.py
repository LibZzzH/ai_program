"""
时间感知幻觉破除器 — 启动脚本
直接在终端运行：python start_web.py
"""

import subprocess
import sys
import os
import time


def main():
    print("=" * 56)
    print("  ⏰  时间感知幻觉破除器  v1.0")
    print("=" * 56)
    print()

    print("[1/4] 检查 Python 环境...", end=" ")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"✅ Python {py_ver}")

    print("[2/4] 检查依赖库...", end=" ")
    try:
        import streamlit as st
        print("✅ Streamlit 已就绪")
    except ImportError:
        print("❌ 未安装 Streamlit")
        print()
        print("  正在尝试安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "-q"])
        print("  ✅ Streamlit 安装完成")
        import streamlit as st

    try:
        import pandas
        print("   ✅ pandas 已就绪")
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "-q"])
        print("   ✅ pandas 安装完成")

    print("[3/4] 初始化数据库...", end=" ")
    from utils.db import init_db
    init_db()
    print("✅ 数据库就绪")

    print("[4/4] 启动 Web 服务...")
    print()
    print("  ┌──────────────────────────────────────────────────────┐")
    print("  │                                                      │")
    print("  │   🌐 本地访问地址：http://localhost:8501              │")
    print("  │                                                      │")
    print("  │   📝 首次使用请先注册账号                            │")
    print("  │   🔐 用户ID仅支持英文，3-20位，字母开头              │")
    print("  │                                                      │")
    print("  │   ⌨️  按 Ctrl+C 可停止服务                            │")
    print("  │                                                      │")
    print("  └──────────────────────────────────────────────────────┘")
    print()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", app_path,
             "--server.port", "8501",
             "--browser.serverAddress", "localhost"],
            cwd=script_dir,
            check=True
        )
    except KeyboardInterrupt:
        print()
        print("  ⏹️  服务已停止。下次再见！")
        print()
    except Exception as e:
        print()
        print(f"  ❌ 启动失败：{e}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()