#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print "请先按 README.md 创建 .venv 并安装依赖。"
  exit 1
fi
print "演示地址：http://127.0.0.1:5412"
exec .venv/bin/python -m sign_robot.server --port 5412
