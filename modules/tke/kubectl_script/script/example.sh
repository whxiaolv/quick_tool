#!/bin/sh
# 示例脚本：查看系统信息

rm -rf /letv/logs/acc.log

echo "=== 当前目录结构 ==="
ls -la /letv/logs 2>/dev/null || echo "目录 /letv/logs 不存在"

echo ""
echo "=== 磁盘使用情况 ==="
df -h

echo ""
echo "=== 内存使用情况 ==="
free -m

echo ""
echo "=== 系统信息 ==="
uname -a
