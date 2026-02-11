# 重构测试验证指南

> **目的**: 为每个重构阶段提供明确的、可人工验证的测试方案  
> **原则**: 每个阶段都必须通过全部测试才能进入下一阶段

---

## 📋 测试准备（Phase 0）

### 准备工作清单

#### 1. 建立基准测试环境

```bash
# 1.1 创建基准输出目录
mkdir -p tests/baseline_outputs
mkdir -p tests/regression_outputs

# 1.2 记录当前环境信息
python --version > tests/baseline_outputs/environment.txt
pip list >> tests/baseline_outputs/environment.txt
git rev-parse HEAD >> tests/baseline_outputs/environment.txt
```

#### 2. 生成基准 GDS 文件

```bash
# 2.1 运行所有示例配置
cd /Users/cxjh168/Downloads/Summer-GDS

for config in examples/*.yaml; do
    echo "处理: $config"
    python main.py "$config"
    
    # 保存基准文件
    config_name=$(basename "$config" .yaml)
    mv output.gds "tests/baseline_outputs/${config_name}.gds"
    
    # 记录日志
    echo "✓ ${config_name}.gds 已生成" >> tests/baseline_outputs/generation.log
done

# 2.2 验证所有文件已生成
ls -lh tests/baseline_outputs/*.gds
```

**人工验证步骤**:
- [ ] 检查 `tests/baseline_outputs/` 目录下有多少个 `.gds` 文件
- [ ] 用 KLayout 打开 3-5 个基准文件，确认图形正常显示
- [ ] 记录文件数量: _______ 个

#### 3. 运行现有测试套件

```bash
# 3.1 运行所有测试
pytest tests/ -v --tb=short > tests/baseline_outputs/test_results.txt 2>&1

# 3.2 查看测试结果
cat tests/baseline_outputs/test_results.txt | grep -E "(PASSED|FAILED|ERROR)"

# 3.3 记录测试统计
pytest tests/ --tb=no --quiet | tail -5
```

**人工验证步骤**:
- [ ] 所有测试是否通过？ 是 / 否
- [ ] 如果有失败，记录失败的测试: _______________________
- [ ] 测试通过率: _______% (必须 100%)

#### 4. 创建 GDS 对比脚本

```bash
# 创建对比脚本
cat > tests/scripts/compare_gds.py << 'EOF'
#!/usr/bin/env python3
"""GDS 文件对比工具"""
import sys
import os
from pathlib import Path

def compare_gds_files(baseline_file, new_file):
    """对比两个 GDS 文件"""
    # 简单对比：文件大小
    baseline_size = os.path.getsize(baseline_file)
    new_size = os.path.getsize(new_file)
    
    size_diff = abs(baseline_size - new_size)
    size_diff_percent = (size_diff / baseline_size) * 100 if baseline_size > 0 else 0
    
    print(f"基准文件: {baseline_size} bytes")
    print(f"新文件:   {new_size} bytes")
    print(f"差异:     {size_diff} bytes ({size_diff_percent:.2f}%)")
    
    # 允许 1% 的差异（可能是浮点数精度导致）
    if size_diff_percent > 1.0:
        print("⚠️  警告: 文件大小差异超过 1%")
        return False
    else:
        print("✓ 文件大小差异在允许范围内")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python compare_gds.py <baseline.gds> <new.gds>")
        sys.exit(1)
    
    baseline = sys.argv[1]
    new = sys.argv[2]
    
    if not os.path.exists(baseline):
        print(f"错误: 基准文件不存在: {baseline}")
        sys.exit(1)
    
    if not os.path.exists(new):
        print(f"错误: 新文件不存在: {new}")
        sys.exit(1)
    
    result = compare_gds_files(baseline, new)
    sys.exit(0 if result else 1)
EOF

chmod +x tests/scripts/compare_gds.py
```

**人工验证步骤**:
- [ ] 脚本是否创建成功？
- [ ] 测试脚本: `python tests/scripts/compare_gds.py tests/baseline_outputs/m1.gds tests/baseline_outputs/m1.gds`
- [ ] 输出是否显示 "✓ 文件大小差异在允许范围内"？

---

## 🔧 Week 1 测试验证

### Day 3-4: utils.py 拆分验证

#### 测试 1: 导入兼容性测试

```bash
# 1.1 测试旧的导入方式
python3 << 'EOF'
from gds_utils.utils import logger, um_to_db, setup_logging
from gds_utils.utils import set_global_dbu, get_global_dbu
from gds_utils.utils import validate_precision_dbu, round_vertices

print("✓ 所有旧导入方式正常")
EOF
```

**人工验证**:
- [ ] 是否输出 "✓ 所有旧导入方式正常"？
- [ ] 是否有任何 ImportError？

#### 测试 2: 新模块功能测试

```bash
# 2.1 测试 logger 模块
python3 << 'EOF'
from gds_utils.logger import setup_logging, logger

setup_logging(show_log=False)
logger.info("测试日志")
print("✓ logger 模块正常")
EOF

# 2.2 测试 units 模块
python3 << 'EOF'
from gds_utils.units import set_global_dbu, get_global_dbu, um_to_db

set_global_dbu(0.001)
assert get_global_dbu() == 0.001
assert um_to_db(1.0) == 1000
print("✓ units 模块正常")
EOF

# 2.3 测试 precision 模块
python3 << 'EOF'
from gds_utils.precision import validate_precision_dbu, round_vertices

validate_precision_dbu(0.01, 0.001)  # 应该通过
vertices = [(1.2345, 2.3456), (3.4567, 4.5678)]
rounded = round_vertices(vertices, 0.01)
print(f"原始: {vertices}")
print(f"四舍五入: {rounded}")
print("✓ precision 模块正常")
EOF
```

**人工验证**:
- [ ] 所有模块是否都输出 "✓ ... 模块正常"？
- [ ] 是否有任何错误？

#### 测试 3: 回归测试

```bash
# 3.1 重新生成所有 GDS 文件
for config in examples/*.yaml; do
    config_name=$(basename "$config" .yaml)
    echo "测试: $config_name"
    
    python main.py "$config"
    mv output.gds "tests/regression_outputs/${config_name}.gds"
    
    # 对比基准文件
    python tests/scripts/compare_gds.py \
        "tests/baseline_outputs/${config_name}.gds" \
        "tests/regression_outputs/${config_name}.gds"
    
    if [ $? -eq 0 ]; then
        echo "✓ ${config_name} 对比通过"
    else
        echo "✗ ${config_name} 对比失败"
    fi
done
```

**人工验证**:
- [ ] 所有配置是否都显示 "✓ ... 对比通过"？
- [ ] 如果有失败，记录失败的配置: _______________________
- [ ] 用 KLayout 打开 2-3 个新生成的文件，目视检查是否正常

#### 测试 4: 单元测试

```bash
# 4.1 运行所有测试
pytest tests/ -v

# 4.2 检查测试覆盖率
pytest tests/ --cov=gds_utils --cov-report=term-missing
```

**人工验证**:
- [ ] 所有测试是否通过？
- [ ] 测试覆盖率是否 ≥ 之前的基准？
- [ ] 记录覆盖率: _______%

#### 测试 5: 性能测试

```bash
# 5.1 测试生成速度
time python main.py examples/m1.yaml

# 5.2 对比基准时间（记录在 baseline_outputs/performance.txt）
echo "重构后时间:" >> tests/regression_outputs/performance.txt
time python main.py examples/m1.yaml 2>> tests/regression_outputs/performance.txt
```

**人工验证**:
- [ ] 生成时间是否与基准相近（差异 < 10%）？
- [ ] 基准时间: _______ 秒
- [ ] 重构后时间: _______ 秒

---

### Day 5-7: Web GUI 拆分验证

#### 测试 1: Web 服务启动测试

```bash
# 1.1 启动 Web 服务
cd web_gui
python app.py &
WEB_PID=$!

# 等待服务启动
sleep 3

# 检查服务是否运行
curl http://localhost:5000/ > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Web 服务启动成功"
else
    echo "✗ Web 服务启动失败"
fi

# 停止服务
kill $WEB_PID
```

**人工验证**:
- [ ] 服务是否启动成功？
- [ ] 浏览器访问 http://localhost:5000 是否正常显示？

#### 测试 2: API 功能测试

```bash
# 2.1 测试默认配置 API
curl -X GET http://localhost:5000/api/default-config | python -m json.tool

# 2.2 测试配置验证 API
curl -X POST http://localhost:5000/api/validate-config \
    -H "Content-Type: application/json" \
    -d @examples/m1.yaml

# 2.3 测试 GDS 生成 API
curl -X POST http://localhost:5000/api/generate-gds \
    -H "Content-Type: application/json" \
    -d @examples/m1.yaml \
    -o test_output.gds

# 检查生成的文件
ls -lh test_output.gds
```

**人工验证**:
- [ ] 默认配置 API 是否返回 JSON？
- [ ] 配置验证 API 是否正常工作？
- [ ] GDS 生成 API 是否返回文件？
- [ ] 生成的文件大小是否合理？

#### 测试 3: Web GUI 手动测试

**操作步骤**:
1. 启动 Web 服务: `cd web_gui && python app.py`
2. 浏览器打开: http://localhost:5000
3. 执行以下操作:

**测试用例 1: 加载配置文件**
- [ ] 点击 "加载配置" 按钮
- [ ] 选择 `examples/m1.yaml`
- [ ] 配置是否正确显示在界面上？

**测试用例 2: 生成 GDS**
- [ ] 点击 "生成 GDS" 按钮
- [ ] 是否开始生成？
- [ ] 是否自动下载 GDS 文件？
- [ ] 用 KLayout 打开下载的文件，是否正常？

**测试用例 3: 配置验证**
- [ ] 修改配置中的 dbu 为无效值（如 -1）
- [ ] 点击 "验证配置"
- [ ] 是否显示错误提示？

**测试用例 4: 保存配置**
- [ ] 修改配置
- [ ] 点击 "保存配置"
- [ ] 是否成功保存？

#### 测试 4: 代码结构检查

```bash
# 4.1 检查新文件是否创建
ls -l web_gui/gds_service.py
ls -l web_gui/routes.py

# 4.2 检查代码行数
wc -l web_gui/app.py web_gui/gds_service.py web_gui/routes.py
```

**人工验证**:
- [ ] 新文件是否创建？
- [ ] app.py 行数是否减少？
- [ ] 代码结构是否更清晰？

---

## 🏗️ Week 2 测试验证

### Day 8-10: Region 方法提取验证

#### 测试 1: 接口兼容性测试

```python
# 创建测试脚本
cat > tests/test_region_refactor.py << 'EOF'
"""测试 Region 重构后的兼容性"""
import pytest
from gds_utils import Frame, Region

def test_create_rings_interface():
    """测试 create_rings 接口未改变"""
    vertices = [(0, 0), (10, 0), (10, 10), (0, 10)]
    frame = Frame(vertices)
    
    # 测试基本调用
    region = Region.create_rings(
        frame,
        ring_width=1.0,
        ring_space=0.5,
        ring_num=3
    )
    
    assert region is not None
    assert not region.get_klayout_region().is_empty()

def test_create_rings_with_fillet():
    """测试带倒角的环生成"""
    vertices = [(0, 0), (10, 0), (10, 10), (0, 10)]
    frame = Frame(vertices)
    
    fillet_config = {
        "type": "arc",
        "radius": 0.5,
        "precision": 0.01
    }
    
    region = Region.create_rings(
        frame,
        ring_width=1.0,
        ring_space=0.5,
        ring_num=3,
        fillet_config=fillet_config
    )
    
    assert region is not None
    assert not region.get_klayout_region().is_empty()

def test_private_methods_exist():
    """测试私有方法是否存在"""
    assert hasattr(Region, '_normalize_ring_params')
    assert hasattr(Region, '_build_radius_configs')
    assert hasattr(Region, '_generate_individual_rings')
    assert hasattr(Region, '_merge_rings')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF

# 运行测试
python tests/test_region_refactor.py
```

**人工验证**:
- [ ] 所有测试是否通过？
- [ ] 是否有任何 AttributeError？

#### 测试 2: 功能回归测试

```bash
# 2.1 测试所有 rings 类型的配置
for config in examples/*rings*.yaml; do
    echo "测试: $(basename $config)"
    python main.py "$config"
    
    config_name=$(basename "$config" .yaml)
    python tests/scripts/compare_gds.py \
        "tests/baseline_outputs/${config_name}.gds" \
        "output.gds"
done
```

**人工验证**:
- [ ] 所有 rings 配置是否对比通过？
- [ ] 如果有差异，记录: _______________________

#### 测试 3: 代码可读性检查

**人工检查清单**:
- [ ] 打开 `gds_utils/region.py`
- [ ] `create_rings` 方法是否更短（< 50 行）？
- [ ] 私有方法是否有清晰的文档字符串？
- [ ] 逻辑是否更容易理解？

---

### Day 11-14: 测试补充验证

#### 测试 1: 新增单元测试

```bash
# 1.1 运行新增的单元测试
pytest tests/unit/ -v

# 1.2 检查覆盖率
pytest tests/unit/ --cov=gds_utils --cov-report=html
```

**人工验证**:
- [ ] 新增测试是否通过？
- [ ] 覆盖率是否提升？
- [ ] 打开 `htmlcov/index.html` 查看详细覆盖率报告
- [ ] 覆盖率: _______%（目标 > 70%）

#### 测试 2: 集成测试

```bash
# 2.1 运行集成测试
pytest tests/integration/ -v
```

**人工验证**:
- [ ] 集成测试是否通过？
- [ ] Web API 测试是否正常？

#### 测试 3: 回归测试套件

```bash
# 3.1 运行完整回归测试
pytest tests/regression/ -v

# 3.2 生成测试报告
pytest tests/ --html=tests/report.html --self-contained-html
```

**人工验证**:
- [ ] 回归测试是否全部通过？
- [ ] 打开 `tests/report.html` 查看详细报告
- [ ] 是否有任何失败或警告？

---

## 📚 Week 3 测试验证

### Day 15-17: 文档验证

#### 测试 1: 文档完整性检查

**检查清单**:
- [ ] `docs/ARCHITECTURE.md` 是否存在？
- [ ] `docs/DEVELOPER_GUIDE.md` 是否存在？
- [ ] `README.md` 是否更新？
- [ ] 所有代码是否有文档字符串？

#### 测试 2: 文档准确性验证

**操作步骤**:
1. 按照 `docs/DEVELOPER_GUIDE.md` 的步骤操作
2. 验证每个步骤是否可执行

**验证清单**:
- [ ] 环境搭建步骤是否正确？
- [ ] 代码示例是否可运行？
- [ ] 配置说明是否清晰？

---

### Day 18-21: 代码审查验证

#### 审查清单

**代码风格**:
- [ ] 所有函数是否有文档字符串？
- [ ] 变量命名是否清晰？
- [ ] 是否遵循 PEP 8 规范？

**代码质量**:
- [ ] 是否有重复代码？
- [ ] 是否有过长的函数（> 50 行）？
- [ ] 是否有复杂的嵌套（> 3 层）？

**测试覆盖**:
- [ ] 关键函数是否有测试？
- [ ] 边界条件是否测试？
- [ ] 异常情况是否测试？

**性能**:
- [ ] 是否有性能退化？
- [ ] 内存使用是否正常？

---

## ✅ Week 4 最终验证

### Day 22-25: 全量测试

#### 完整测试流程

```bash
# 1. 清理环境
rm -rf tests/regression_outputs/*
rm -f output.gds

# 2. 运行所有测试
pytest tests/ -v --tb=short

# 3. 生成所有示例 GDS
for config in examples/*.yaml; do
    python main.py "$config"
    config_name=$(basename "$config" .yaml)
    mv output.gds "tests/regression_outputs/${config_name}.gds"
done

# 4. 对比所有基准文件
for baseline in tests/baseline_outputs/*.gds; do
    filename=$(basename "$baseline")
    python tests/scripts/compare_gds.py \
        "$baseline" \
        "tests/regression_outputs/$filename"
done

# 5. 性能测试
echo "性能测试结果:" > tests/final_performance.txt
for config in examples/*.yaml; do
    echo "配置: $(basename $config)" >> tests/final_performance.txt
    time python main.py "$config" 2>> tests/final_performance.txt
done

# 6. Web GUI 测试
cd web_gui
python -m pytest tests/qt/ -v
```

**最终验收清单**:
- [ ] 所有单元测试通过（100%）
- [ ] 所有集成测试通过（100%）
- [ ] 所有回归测试通过（100%）
- [ ] 所有 GDS 文件对比通过
- [ ] 性能无明显退化（< 10%）
- [ ] Web GUI 功能正常
- [ ] 测试覆盖率 ≥ 70%

---

### Day 26-28: 发布前检查

#### 最终检查清单

**功能检查**:
- [ ] 所有示例配置可正常运行
- [ ] Web GUI 所有功能正常
- [ ] 命令行工具正常工作

**文档检查**:
- [ ] README 准确完整
- [ ] API 文档完整
- [ ] 示例代码可运行

**代码检查**:
- [ ] 无 TODO 或 FIXME 注释
- [ ] 无调试代码
- [ ] 无临时文件

**版本检查**:
- [ ] 版本号已更新
- [ ] CHANGELOG 已编写
- [ ] Git 标签已创建

---

## 📊 测试记录表

### 阶段完成记录

| 阶段 | 日期 | 测试通过率 | GDS对比 | 性能 | 签名 |
|------|------|-----------|---------|------|------|
| Phase 0 准备 | ______ | ___% | ✓/✗ | ___s | ____ |
| Week 1 Day 3-4 | ______ | ___% | ✓/✗ | ___s | ____ |
| Week 1 Day 5-7 | ______ | ___% | ✓/✗ | ___s | ____ |
| Week 2 Day 8-10 | ______ | ___% | ✓/✗ | ___s | ____ |
| Week 2 Day 11-14 | ______ | ___% | ✓/✗ | ___s | ____ |
| Week 3 | ______ | ___% | ✓/✗ | ___s | ____ |
| Week 4 最终 | ______ | ___% | ✓/✗ | ___s | ____ |

### 问题记录

| 日期 | 阶段 | 问题描述 | 解决方案 | 状态 |
|------|------|---------|---------|------|
| | | | | |
| | | | | |

---

## 🚨 失败处理流程

### 如果测试失败

1. **记录失败信息**
   - 失败的测试名称
   - 错误信息
   - 复现步骤

2. **分析原因**
   - 是代码问题还是测试问题？
   - 是否影响核心功能？
   - 影响范围有多大？

3. **决策**
   - **轻微问题**: 修复后继续
   - **严重问题**: 回滚到上一个标签
   - **设计问题**: 重新评估方案

4. **回滚步骤**
```bash
# 查看可用标签
git tag -l "refactor-*"

# 回滚到指定标签
git checkout refactor-week1

# 重新开始
git checkout -b refactor/retry
```

---

**文档版本**: v1.0  
**最后更新**: 2025-02-11  
**维护者**: AI Assistant

