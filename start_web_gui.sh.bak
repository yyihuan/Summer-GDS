#!/bin/bash

# 设置变量
GUI_DIR="./web_gui"
HOST="0.0.0.0"
PORT="5001"
DEBUG=false
CONFIG_PATH=""
HOST_OVERRIDE=false
PORT_OVERRIDE=false
DEBUG_OVERRIDE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --host=*)
      HOST="${1#*=}"
      HOST_OVERRIDE=true
      shift
      ;;
    --port=*)
      PORT="${1#*=}"
      PORT_OVERRIDE=true
      shift
      ;;
    --debug)
      DEBUG=true
      DEBUG_OVERRIDE=true
      shift
      ;;
    --config=*)
      CONFIG_PATH="${1#*=}"
      shift
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

# 如果指定了配置文件，读取配置
if [[ -n "$CONFIG_PATH" ]]; then
  if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "错误: 配置文件 $CONFIG_PATH 不存在"
    exit 1
  fi

  CONFIG_VALUES=$(python - <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

host = data.get('webgui_host')
port = data.get('webgui_port')
debug = data.get('debug')
auto_open = data.get('auto_open_browser')

print(host if host is not None else '')
print(port if port is not None else '')
print('true' if debug else ('false' if debug is not None else ''))
print('true' if auto_open else ('false' if auto_open is not None else ''))
PY
"$CONFIG_PATH")

  IFS=$'\n' read -r CONFIG_HOST CONFIG_PORT CONFIG_DEBUG CONFIG_AUTO_OPEN <<< "$CONFIG_VALUES"

  if [[ -n "$CONFIG_HOST" && $HOST_OVERRIDE == false ]]; then
    HOST="$CONFIG_HOST"
  fi
  if [[ -n "$CONFIG_PORT" && $PORT_OVERRIDE == false ]]; then
    PORT="$CONFIG_PORT"
  fi
  if [[ -n "$CONFIG_DEBUG" && $DEBUG_OVERRIDE == false ]]; then
    if [[ "$CONFIG_DEBUG" == "true" ]]; then
      DEBUG=true
    else
      DEBUG=false
    fi
  fi
else
  CONFIG_AUTO_OPEN=""
fi

AUTO_OPEN_BROWSER="$CONFIG_AUTO_OPEN"

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
  uv add -r requirements.txt
  if [ $? -eq 0 ]; then
    touch .deps_installed
    echo "依赖安装完成"
  else
    echo "依赖安装失败"
    exit 1
  fi
fi

# 构建启动命令
CMD=(python run.py --host "$HOST" --port "$PORT")
if [ "$DEBUG" = true ]; then
  CMD+=(--debug)
fi
if [[ -n "$CONFIG_PATH" ]]; then
  CMD+=(--config "$CONFIG_PATH")
fi
if [[ "$AUTO_OPEN_BROWSER" == "false" ]]; then
  CMD+=(--no-browser)
fi

# 显示信息
echo "启动Summer-GDS Web GUI"
echo "地址: http://$HOST:$PORT"
printf -v CMD_STR '%q ' "${CMD[@]}"
echo "命令: ${CMD_STR% }"
echo "----------------------------------"

# 执行命令
"${CMD[@]}"
