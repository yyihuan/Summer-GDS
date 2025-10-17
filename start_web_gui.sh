#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$SCRIPT_DIR"

cat <<'MSG'
[提示] start_web_gui.sh 已弃用。
请改用：uv run python -m web_gui.qt_launcher [参数]
当前脚本会继续调用新的 Python 启动器以保持兼容。
MSG

exec uv run python -m web_gui.qt_launcher "$@"
