#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Summer-GDS Web GUI 启动脚本
"""

import os
import sys
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

    args = parser.parse_args()

    # 导入应用
    from app import app

    # 启动浏览器(除非禁用)
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.host, args.port), daemon=True).start()

    # 运行应用
    print(f"Summer-GDS Web GUI 正在启动...")
    print(f"访问地址: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print(f"按 Ctrl+C 停止服务器")

    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    # 添加当前目录到路径
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    main() 