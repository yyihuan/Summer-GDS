#!/bin/bash

# Summer-GDS PyInstaller 打包脚本
# 使用 onedir 模式打包

set -e  # 遇到错误立即退出

echo "========================================"
echo "  Summer-GDS PyInstaller 打包脚本"
echo "========================================"
echo ""

# 检查 pyinstaller 是否安装
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: PyInstaller 未安装"
    echo "请运行: pip install pyinstaller"
    exit 1
fi

# 清理之前的构建
echo "清理之前的构建..."
if [ -d "dist" ]; then
    rm -rf dist
    echo "  - 已删除 dist/"
fi
if [ -d "build" ]; then
    rm -rf build
    echo "  - 已删除 build/"
fi
echo ""

# 执行打包
echo "开始打包..."
echo "模式: onedir"
echo "配置文件: SummerGDS.spec"
echo ""

pyinstaller SummerGDS.spec

# 检查打包是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  打包完成!"
    echo "========================================"
    echo ""
    echo "输出目录: ./dist/SummerGDS/"
    echo "可执行文件: ./dist/SummerGDS/SummerGDS"
    echo ""
    echo "使用方法:"
    echo "  cd dist/SummerGDS"
    echo "  ./SummerGDS"
    echo ""
    echo "注意事项:"
    echo "1. 首次运行时会在可执行文件同级目录创建 temp/ 和 uploads/ 文件夹"
    echo "2. 生成的 GDS 文件会保存在 temp/ 目录中"
    echo "3. 默认会自动打开浏览器,使用 --no-browser 参数可禁用"
    echo "4. 默认端口为 5000,可用 --port 参数修改"
    echo ""

    # 显示打包大小
    if command -v du &> /dev/null; then
        SIZE=$(du -sh dist/SummerGDS | cut -f1)
        echo "打包大小: $SIZE"
        echo ""
    fi
else
    echo ""
    echo "========================================"
    echo "  打包失败!"
    echo "========================================"
    echo "请检查上方的错误信息"
    exit 1
fi
