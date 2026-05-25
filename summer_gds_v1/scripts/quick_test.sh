#!/bin/bash
# 快速人工测试脚本

set -e

echo "🧪 开始快速测试..."
echo ""

# 1. 运行单元测试
echo "1️⃣ 运行单元测试..."
uv run pytest tests/ -q
if [ $? -eq 0 ]; then
    echo "✅ 单元测试通过"
else
    echo "❌ 单元测试失败"
    exit 1
fi
echo ""

# 2. 生成测试 GDS
echo "2️⃣ 生成测试 GDS 文件..."
uv run python main.py examples/m1.yaml
mv output.gds m1_test.gds
echo "✅ 已生成 m1_test.gds"
echo ""

# 3. 对比 MD5
echo "3️⃣ 对比 MD5 值..."
baseline_md5=$(md5 -q tests/baseline_outputs/m1.gds)
test_md5=$(md5 -q m1_test.gds)

echo "基准 MD5: $baseline_md5"
echo "测试 MD5: $test_md5"

if [ "$baseline_md5" = "$test_md5" ]; then
    echo "✅ MD5 完全匹配"
    echo ""
    echo "🎉 测试通过！文件完全一致。"
else
    echo "⚠️  MD5 不匹配"
    echo ""
    echo "4️⃣ 打开 KLayout 进行可视化对比..."
    echo "请在 KLayout 中："
    echo "  1. 查看两个文件的图形是否一致"
    echo "  2. 使用 Tools → Boolean Operations → XOR 进行对比"
    echo "  3. 如果 XOR 结果为空，说明图形完全一致"
    echo ""
    
    # 检查 KLayout 是否安装
    if command -v klayout &> /dev/null; then
        klayout tests/baseline_outputs/m1.gds m1_test.gds
    else
        echo "⚠️  未检测到 KLayout，请手动打开文件对比："
        echo "   基准文件: tests/baseline_outputs/m1.gds"
        echo "   测试文件: m1_test.gds"
    fi
fi

echo ""
echo "📝 测试完成！"

