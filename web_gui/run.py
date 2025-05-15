#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Summer-GDS Web GUI 启动脚本
"""

import os
import sys
import argparse

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动Summer-GDS Web GUI')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 导入应用
    from app import app
    
    # 运行应用
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    # 添加当前目录到路径
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    main() 