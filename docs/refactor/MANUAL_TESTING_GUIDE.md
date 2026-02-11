# 人工测试指南

> **目的**: 提供直观的、可视化的测试方法来验证重构的正确性  
> **适用**: 每个重构阶段完成后

---

## 🎯 测试目标

通过人工查看和对比 GDS 文件，确保重构后：
1. ✅ 生成的 GDS 文件与基准文件一致
2. ✅ 图形显示正常，无异常
3. ✅ 所有功能正常工作

---

## 📦 准备工作

### 1. 安装 KLayout（如果还没有）

KLayout 是查看 GDS 文件的标准工具。

**macOS 安装**:
```bash
# 方法1: 使用 Homebrew
brew install --cask klayout

# 方法2: 从官网下载
# https://www.klayout.de/build.html
```

**验证安装**:
```bash
klayout -v
```

### 2. 确认基准文件已生成

```bash
cd /Users/cxjh168/Downloads/Summer-GDS
ls -lh tests/baseline_outputs/*.gds
```

应该看到 6 个基准 GDS 文件：
- m1.gds
- new.gds
- new2.gds
- precision_test_punch.gds
- rings_width_space_rule.gds
- test_pd.gds

---

## 🔍 测试方法

### 方法 1: 使用 KLayout 可视化对比（推荐）

这是最直观的方法，可以直接看到图形差异。

#### 步骤 1: 生成新的 GDS 文件

```bash
cd /Users/cxjh168/Downloads/Summer-GDS

# 生成一个测试文件
uv run python main.py examples/m1.yaml

# 文件会生成为 output.gds
```

#### 步骤 2: 用 KLayout 打开基准文件

```bash
# 打开基准文件
klayout tests/baseline_outputs/m1.gds
```

**在 KLayout 中查看**:
1. 查看所有图层是否正常显示
2. 检查形状是否完整
3. 截图保存（可选）

#### 步骤 3: 用 KLayout 打开新生成的文件

```bash
# 打开新文件
klayout output.gds
```

**对比检查**:
- [ ] 图层数量是否相同？
- [ ] 形状数量是否相同？
- [ ] 形状位置是否相同？
- [ ] 倒角是否正确？

#### 步骤 4: 使用 KLayout 的对比功能

```bash
# 同时打开两个文件进行对比
klayout tests/baseline_outputs/m1.gds output.gds
```

**在 KLayout 中**:
1. 点击 `Tools` → `XOR`
2. 选择两个文件的相同图层
3. 执行 XOR 操作
4. **如果结果为空，说明两个文件完全一致** ✅

---

### 方法 2: 使用对比脚本

我们已经创建了自动对比脚本。

#### 快速对比所有文件

```bash
cd /Users/cxjh168/Downloads/Summer-GDS

# 先生成所有新的 GDS 文件到当前目录
for config in examples/m1.yaml examples/new.yaml examples/new2.yaml; do
    uv run python main.py "$config"
    config_name=$(basename "$config" .yaml)
    mv output.gds "${config_name}_new.gds"
done

# 使用对比脚本
uv run python scripts/compare_gds.py tests/baseline_outputs .
```

**查看输出**:
- ✅ 绿色勾号 = 文件匹配
- ❌ 红色叉号 = 文件不匹配

---

### 方法 3: 手动检查文件属性

这是最简单但不够精确的方法。

```bash
cd /Users/cxjh168/Downloads/Summer-GDS

# 对比文件大小
ls -lh tests/baseline_outputs/m1.gds
ls -lh output.gds

# 对比文件哈希值（最精确）
md5 tests/baseline_outputs/m1.gds
md5 output.gds
```

**判断标准**:
- 如果 MD5 值完全相同 → ✅ 完全一致
- 如果文件大小相差 < 1% → ⚠️ 可能有微小差异，需要用 KLayout 检查
- 如果文件大小相差 > 1% → ❌ 有明显差异，需要调查

---

## 📝 测试清单

### Phase 0 验证清单

完成 Phase 0 后，执行以下检查：

```bash
cd /Users/cxjh168/Downloads/Summer-GDS

# 1. 运行所有测试
uv run pytest tests/ -v
```

**人工检查**:
- [ ] 所有 85 个测试都通过了吗？

```bash
# 2. 检查基准文件
ls -lh tests/baseline_outputs/*.gds
```

**人工检查**:
- [ ] 有 6 个 .gds 文件吗？
- [ ] 文件大小都 > 0 吗？

```bash
# 3. 用 KLayout 打开一个基准文件
klayout tests/baseline_outputs/m1.gds
```

**人工检查**:
- [ ] 文件能正常打开吗？
- [ ] 能看到图形吗？
- [ ] 图形看起来正常吗（没有明显错误）？

---

### Week 1 Day 3-4 验证清单（utils.py 拆分后）

完成 utils.py 拆分后，执行以下检查：

```bash
cd /Users/cxjh168/Downloads/Summer-GDS

# 1. 运行所有测试
uv run pytest tests/ -v
```

**人工检查**:
- [ ] 所有测试仍然通过吗？

```bash
# 2. 生成新的 GDS 文件
uv run python main.py examples/m1.yaml
mv output.gds m1_after_refactor.gds

# 3. 对比文件
md5 tests/baseline_outputs/m1.gds
md5 m1_after_refactor.gds
```

**人工检查**:
- [ ] MD5 值完全相同吗？

```bash
# 4. 用 KLayout 可视化对比
klayout tests/baseline_outputs/m1.gds m1_after_refactor.gds
```

**在 KLayout 中执行 XOR 对比**:
- [ ] XOR 结果为空吗（说明完全一致）？

```bash
# 5. 测试所有基准配置
for config in examples/m1.yaml examples/new.yaml examples/new2.yaml \
              examples/precision_test_punch.yaml examples/test_pd.yaml; do
    echo "测试: $config"
    uv run python main.py "$config"
    config_name=$(basename "$config" .yaml)
    
    # 对比 MD5
    baseline_md5=$(md5 -q "tests/baseline_outputs/${config_name}.gds")
    new_md5=$(md5 -q "output.gds")
    
    if [ "$baseline_md5" = "$new_md5" ]; then
        echo "✅ ${config_name}: 匹配"
    else
        echo "❌ ${config_name}: 不匹配"
    fi
done
```

**人工检查**:
- [ ] 所有配置都显示 ✅ 匹配吗？

---

## 🎨 KLayout 使用技巧

### 基本操作

1. **打开文件**: `File` → `Open` 或 `klayout file.gds`
2. **缩放**: 鼠标滚轮 或 `F2`（适应窗口）
3. **平移**: 按住鼠标中键拖动
4. **图层控制**: 左侧面板可以显示/隐藏图层

### 对比两个文件

1. **打开两个文件**:
   ```bash
   klayout baseline.gds new.gds
   ```

2. **切换视图**: 
   - 点击顶部的标签页切换文件
   - 或使用 `Window` → `Tile` 并排显示

3. **XOR 对比**:
   - `Tools` → `Boolean Operations` → `XOR`
   - 选择两个文件的相同图层
   - 点击 `Execute`
   - **如果结果为空 = 完全一致** ✅

### 测量和检查

1. **测量距离**: `Tools` → `Ruler`
2. **查看顶点**: 选中形状，右键 → `Properties`
3. **查看图层信息**: 点击图层面板中的图层

---

## 📊 测试记录表

### Phase 0 测试记录

| 检查项 | 预期结果 | 实际结果 | 通过? |
|--------|---------|---------|-------|
| 单元测试通过 | 85/85 | ___/85 | ☐ |
| 基准文件数量 | 6 个 | ___ 个 | ☐ |
| m1.gds 可打开 | 能打开 | _______ | ☐ |
| new.gds 可打开 | 能打开 | _______ | ☐ |
| 图形显示正常 | 正常 | _______ | ☐ |

**测试日期**: ___________  
**测试人**: ___________  
**总体结论**: ☐ 通过 / ☐ 不通过

---

### Week 1 Day 3-4 测试记录（utils.py 拆分）

| 检查项 | 预期结果 | 实际结果 | 通过? |
|--------|---------|---------|-------|
| 单元测试通过 | 85/85 | ___/85 | ☐ |
| m1.gds MD5 匹配 | 匹配 | _______ | ☐ |
| new.gds MD5 匹配 | 匹配 | _______ | ☐ |
| new2.gds MD5 匹配 | 匹配 | _______ | ☐ |
| KLayout XOR 对比 | 为空 | _______ | ☐ |
| 所有配置测试 | 全部匹配 | ___/6 匹配 | ☐ |

**测试日期**: ___________  
**测试人**: ___________  
**总体结论**: ☐ 通过 / ☐ 不通过

---

## 🚨 常见问题

### Q1: KLayout 打不开 GDS 文件

**可能原因**:
- 文件损坏
- 文件格式不正确
- 文件为空

**解决方法**:
```bash
# 检查文件大小
ls -lh file.gds

# 检查文件类型
file file.gds

# 重新生成文件
uv run python main.py config.yaml
```

### Q2: XOR 对比结果不为空

**可能原因**:
- 浮点数精度差异
- 顶点顺序不同（但形状相同）
- 实际的代码变更导致输出不同

**解决方法**:
1. 检查 XOR 结果的大小（如果非常小，可能是精度问题）
2. 用肉眼对比两个文件，看是否有明显差异
3. 检查代码变更，确认是否有意外修改

### Q3: MD5 值不同但 KLayout 看起来一样

**可能原因**:
- GDS 文件包含时间戳等元数据
- 浮点数精度微小差异

**解决方法**:
- 以 KLayout 的可视化对比为准
- 如果 XOR 结果为空或非常小，可以认为是一致的

---

## 🎯 快速测试脚本

创建一个快速测试脚本：

```bash
cat > quick_test.sh << 'EOF'
#!/bin/bash
# 快速人工测试脚本

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
else
    echo "⚠️  MD5 不匹配，请用 KLayout 检查"
fi
echo ""

# 4. 打开 KLayout 进行可视化对比
echo "4️⃣ 打开 KLayout 进行可视化对比..."
echo "请在 KLayout 中执行 XOR 对比"
klayout tests/baseline_outputs/m1.gds m1_test.gds

echo ""
echo "🎉 测试完成！"
EOF

chmod +x quick_test.sh
```

**使用方法**:
```bash
./quick_test.sh
```

---

## 📚 总结

### 推荐的测试流程

每次重构后，按以下顺序测试：

1. **自动化测试** (必须)
   ```bash
   uv run pytest tests/ -v
   ```

2. **MD5 对比** (快速检查)
   ```bash
   uv run python scripts/compare_gds.py tests/baseline_outputs
   ```

3. **KLayout 可视化** (最终确认)
   ```bash
   klayout tests/baseline_outputs/m1.gds output.gds
   # 执行 XOR 对比
   ```

### 判断标准

- ✅ **通过**: 单元测试通过 + MD5 匹配 + KLayout XOR 为空
- ⚠️ **需检查**: 单元测试通过 + MD5 不匹配 + KLayout 看起来一样
- ❌ **失败**: 单元测试失败 或 KLayout 有明显差异

---

**最后更新**: 2026-02-11  
**文档版本**: v1.0

