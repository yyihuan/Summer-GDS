#!/bin/bash

# 设置变量
GUI_DIR="./web_gui"
HOST="127.0.0.1"
PORT="5001"
DEBUG=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --host=*)
      HOST="${1#*=}"
      shift
      ;;
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

# 检查web_gui目录是否存在
if [ ! -d "$GUI_DIR" ]; then
  echo "错误: $GUI_DIR 目录不存在"
  exit 1
fi

# 进入web_gui目录
cd "$GUI_DIR"

# 检查是否需要安装依赖
if [ ! -f ".deps_installed" ]; then
  echo "正在安装依赖..."
  pip install -r requirements.txt
  if [ $? -eq 0 ]; then
    touch .deps_installed
    echo "依赖安装完成"
  else
    echo "依赖安装失败"
    exit 1
  fi
fi

# 构建启动命令
CMD="python run.py --host $HOST --port $PORT"
if [ "$DEBUG" = true ]; then
  CMD="$CMD --debug"
fi

# 显示信息
echo "启动Summer-GDS Web GUI"
echo "地址: http://$HOST:$PORT"
echo "命令: $CMD"
echo "----------------------------------"

# 执行命令
$CMD 