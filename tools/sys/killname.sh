#!/bin/bash

# 用法: ./killname.sh <进程名关键词>
# 示例: ./killname.sh qemu

if [ $# -eq 0 ]; then
    echo "Usage: $0 <process_name>"
    exit 1
fi

keyword="$1"

# 使用 ps + awk 提取 PID（跳过 grep 自身）
pids=$(ps aux | awk -v kw="$keyword" '
    NR == 1 { next }                # 跳过表头
    /grep/ && !/awk/ { next }       # 跳过 grep 行（包括本脚本可能产生的）
    index($0, kw) && !/killname\.sh/ { print $2 }
')

if [ -z "$pids" ]; then
    echo "No process found matching '$keyword'"
else
    echo "Killing PIDs: $pids"
    kill $pids 2>/dev/null
    # 可选：等待几秒后强制 kill（如果没退出）
    sleep 1
    kill -9 $pids 2>/dev/null
fi

