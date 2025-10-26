# 全局精度控制 - 快速参考卡

## 测试命令速查表

### 快速测试
```bash
# 运行所有自动化测试
source .venv/bin/activate
python -m pytest tests/test_precision*.py -v
```

### 单个配置文件测试
```bash
# 向后兼容（应该成功）
python main.py examples/precision_test_default.yaml

# 精度 0.01 μm（应该成功）
python main.py examples/precision_test_0_01.yaml

# 高精度 0.0001 μm（应该成功）
python main.py examples/precision_test_0_0001.yaml

# 环阵列（应该成功）
python main.py examples/precision_test_rings.yaml

# 错误配置（应该失败）
python main.py examples/precision_test_invalid.yaml

# 复杂多层（应该成功）
python main.py examples/precision_test_complex.yaml

# 性能测试
python main.py examples/precision_test_performance.yaml
```

---

## 配置关键参数

### 有效的 dbu / precision 组合

| dbu | precision | 比例 | 有效 |
|-----|-----------|------|------|
| 0.001 | 0.01 | 10 | ✅ |
| 0.001 | 0.001 | 1 | ✅ |
| 0.0001 | 0.0001 | 1 | ✅ |
| 0.0001 | 0.001 | 10 | ✅ |
| 0.001 | 0.0001 | 0.1 | ❌ 不兼容 |
| 0.001 | 0.00001 | 0.01 | ❌ 不兼容 |

### 配置模板

**最小配置（无精度控制）**
```yaml
global:
  dbu: 0.001
  # precision 不指定
```

**精度控制配置**
```yaml
global:
  dbu: 0.001
  precision: 0.01     # ← 添加这行
```

**高精度配置**
```yaml
global:
  dbu: 0.0001         # ← 改这里
  precision: 0.0001   # ← 和这里
```

---

## 日志检查点

### 成功标志
```
✅ 初始化 GDS：dbu=0.001 μm, precision=0.01 μm
✅ 顶点精度转换：precision=0.01, 点数=4
✅ 保存GDS文件: output_xxx.gds
```

### 失败标志
```
❌ precision 和 dbu 不兼容：0.0001 / 0.001 = 0.1，必须是整数倍关系！
❌ precision 必须在 0.00001 ~ 1.0 范围内
❌ dbu 必须在 0.00001 ~ 1.0 范围内
```

---

## 测试清单

### 自动化测试（31个）
- [ ] test_precision_param_recognition.py (16个) - 参数识别
- [ ] test_precision_control.py (15个) - 精度控制和bool操作

### 手动测试（6个配置）
- [ ] precision_test_default.yaml - 向后兼容
- [ ] precision_test_0_01.yaml - 0.01μm精度
- [ ] precision_test_0_0001.yaml - 0.0001μm精度
- [ ] precision_test_rings.yaml - 环阵列
- [ ] precision_test_invalid.yaml - 错误配置（应失败）
- [ ] precision_test_complex.yaml - 多层复杂

### 性能测试（可选）
- [ ] precision_test_performance.yaml - 大规模多边形

---

## 常见问题速解

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| `precision 和 dbu 不兼容` | precision/dbu 不是整数 | 确保 precision = dbu × k |
| 顶点没有四舍五入 | precision=None | 在 global 中指定 precision |
| Bool操作失败 | 罕见（已测试覆盖） | 检查参数兼容性 |
| 输出文件为空 | dbu 太大或太小 | 使用推荐值（0.0001~0.001） |

---

## 文件位置速查

| 文件 | 位置 | 说明 |
|-----|------|------|
| 设计方案 | discuss/debug/刻孔失效/01_*.md | 完整设计文档 |
| 执行总结 | discuss/debug/刻孔失效/02_*.md | 阶段一、二总结 |
| 测试指南 | discuss/debug/刻孔失效/03_*.md | 详细测试说明 |
| 配置示例 | examples/precision_test_*.yaml | 6个测试配置 |
| 单元测试 | tests/test_precision_*.py | 31个自动化测试 |

---

## 验收标准

✅ **完全满足**：
- 16/16 参数识别测试通过
- 15/15 精度控制测试通过
- bool操作精确无误
- 向后兼容性完全保持
- 文档完整清晰

✅ **准备就绪**：
- 后端功能完整测试
- 前端修改（阶段三）可开始
- Web GUI 集成就绪

---

## 下一步（阶段三）

1. **修改 web_gui/app.py**
   - 更新 DEFAULT_CONFIG 中的 dbu 和 precision

2. **修改 Web GUI 模板**
   - "倒角精度" → "全局精度控制"
   - 添加 dbu 输入字段

3. **前端验证**
   - precision % dbu == 0

4. **测试**
   - 端到端功能验证
   - UI交互测试
