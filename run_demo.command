#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print "请先按 README.md 创建 .venv 并安装依赖。"
  exit 1
fi
print "演示地址：http://127.0.0.1:5412"
.venv/bin/python -m sign_robot.service start --port 5412
print "服务已在后台运行。关闭这个终端窗口不会主动停止服务。"
print "状态：.venv/bin/python -m sign_robot.service status"
print "停止：.venv/bin/python -m sign_robot.service stop"
