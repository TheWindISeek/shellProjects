#!/bin/bash

echo "You are about to execute a critical command: reboot"
read -p "Press Enter to continue or Ctrl+C to cancel: " -n 1 -s
echo

# 调用真正的命令
exec "reboot"
