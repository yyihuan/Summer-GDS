#!/bin/bash
# 生成基准 GDS 文件脚本

set -e

BASELINE_DIR="tests/baseline_outputs"
EXAMPLES_DIR="examples"

echo "开始生成基准 GDS 文件..."
echo "================================"

# 确保基准目录存在
mkdir -p "$BASELINE_DIR"

# 计数器
success_count=0
fail_count=0
total_count=0

# 遍历所有 YAML 配置文件
for config in "$EXAMPLES_DIR"/*.yaml; do
    if [ -f "$config" ]; then
        total_count=$((total_count + 1))
        basename=$(basename "$config" .yaml)
        output_file="$BASELINE_DIR/${basename}.gds"
        
        echo "处理: $config"
        
        # 运行生成器
        if uv run python main.py "$config" 2>&1 | tee "$BASELINE_DIR/${basename}.log"; then
            # 检查是否生成了 output.gds
            if [ -f "output.gds" ]; then
                mv output.gds "$output_file"
                echo "✓ 成功: $output_file"
                success_count=$((success_count + 1))
            else
                echo "✗ 失败: 未生成 output.gds"
                fail_count=$((fail_count + 1))
            fi
        else
            echo "✗ 失败: 执行出错"
            fail_count=$((fail_count + 1))
        fi
        echo "--------------------------------"
    fi
done

echo "================================"
echo "生成完成！"
echo "总计: $total_count"
echo "成功: $success_count"
echo "失败: $fail_count"
echo "================================"

# 列出生成的文件
echo ""
echo "生成的基准文件："
ls -lh "$BASELINE_DIR"/*.gds 2>/dev/null || echo "无 GDS 文件"

