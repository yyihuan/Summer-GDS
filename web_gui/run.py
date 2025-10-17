#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Summer-GDS Web GUI 启动脚本
"""

import os
import sys
import json
import argparse
import webbrowser
import threading
import time

# 关键修复:启动时立即切换工作目录到可执行文件所在目录
# 这样无论如何启动(双击/命令行),工作目录都是正确的
if getattr(sys, 'frozen', False):
    # 打包环境:切换到可执行文件所在目录
    os.chdir(os.path.dirname(sys.executable))
else:
    # 开发环境:切换到 web_gui 的父目录(项目根目录)
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def open_browser(host, port, delay=1.5):
    """延迟打开浏览器"""
    time.sleep(delay)
    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    print(f"正在打开浏览器: {url}")
    webbrowser.open(url)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动Summer-GDS Web GUI')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--config', type=str, help='可选配置文件，覆盖 host/port 等默认值')

    args = parser.parse_args()

    config_data = None
    if args.config:
        config_path = os.path.abspath(args.config)
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        provided_args = sys.argv[1:]
        def has_flag(prefix):
            return any(item == prefix or item.startswith(prefix + '=') for item in provided_args)

        if config_data:
            host = config_data.get('webgui_host')
            port = config_data.get('webgui_port')
            debug_flag = config_data.get('debug')
            auto_open = config_data.get('auto_open_browser')

            if host is not None and not has_flag('--host'):
                args.host = host
            if port is not None and not has_flag('--port'):
                args.port = port
            if debug_flag is not None and not has_flag('--debug'):
                args.debug = bool(debug_flag)
            if auto_open is not None and not has_flag('--no-browser'):
                args.no_browser = not bool(auto_open)

    # 导入应用
    from app import app

    # 启动浏览器(除非禁用)
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.host, args.port), daemon=True).start()

    # 运行应用
    print("Summer-GDS Web GUI 正在启动...")
    print(f"访问地址: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    if config_data:
        print(f"使用配置文件: {os.path.abspath(args.config)}")
    print("按 Ctrl+C 停止服务器")

    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    # 添加当前目录到路径
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    main() 
