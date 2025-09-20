#!/bin/bash
# SQLite别名映射快速查看脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIEWER_SCRIPT="$SCRIPT_DIR/sqlite_alias_viewer.py"

# 检查Python3是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 系统中未找到python3命令"
    exit 1
fi

# 检查tabulate是否安装
if ! python3 -c "import tabulate" 2>/dev/null; then
    echo "📦 正在安装tabulate库..."
    pip3 install tabulate
fi

# 如果没有参数，显示基本信息
if [ $# -eq 0 ]; then
    echo "🚀 显示SQLite别名映射的基本信息..."
    python3 "$VIEWER_SCRIPT" all
else
    # 传递所有参数给主脚本
    python3 "$VIEWER_SCRIPT" "$@"
fi
