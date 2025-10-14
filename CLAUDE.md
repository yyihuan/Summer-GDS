# Claude Code 项目指导文档

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## ⚠️ 重要提醒

**README.md 文件可能包含过时信息**：README.md 文件可能没有及时更新，其中某些信息可能与当前代码实现不符。在进行开发工作时，请以实际代码为准，不要完全依赖 README.md 的内容。建议优先参考：
1. 实际代码实现（特别是 `main.py` 和 `gds_utils/` 模块）
2. 本 CLAUDE.md 文件中的架构说明
3. 配置示例文件和测试用例

后续需要更新 README.md 以确保文档与代码同步。

## 项目概述

Summer-GDS 是一个基于 Python 的 GDS (GDSII) 文件生成工具，用于创建复杂的多边形图案和环阵列，具有倒角和缩放等高级功能。它使用 KLayout 的 Python API 进行 GDS 操作，并包含命令行界面和 Web GUI 界面。

## 开发命令

### 运行应用程序

**命令行模式：**
```bash
python main.py <config.yaml>
```

**Web GUI 模式：**
```bash
./start_web_gui.sh
# 或使用自定义参数：
./start_web_gui.sh --host=127.0.0.1 --port=8080 --debug
```

### 测试

从项目根目录运行测试：
```bash
python -m pytest tests/
# 运行特定测试文件：
python -m pytest tests/test_frame.py
```

### 构建

使用 PyInstaller 打包应用程序：
```bash
./build.sh
```

### 依赖管理

使用 pip 或 uv 安装依赖：
```bash
pip install -r requirements.txt
# 或使用 uv（现代方法）：
uv pip install -e .
```

Web GUI 有额外的依赖：
```bash
pip install -r web_gui/requirements.txt
```

## 代码架构

### 核心类层次结构

代码库遵循面向对象的架构，具有清晰的关注点分离：

**GDS → Cell → Region/Frame**

1. **GDS (gds_utils/gds.py)**：管理 KLayout 布局的顶层容器
   - 创建和管理多个单元格
   - 处理文件 I/O（读取/写入 GDS 文件）
   - 设置数据库单位 (dbu) 进行微米到数据库的转换

2. **Cell (gds_utils/cell.py)**：表示 GDS 布局中的单个单元格
   - 通过 LayerManager 管理层信息
   - 将 Region 对象添加到特定层
   - 每个单元格都有自己的层映射

3. **LayerManager (gds_utils/layer.py)**：处理层映射和索引
   - 将 (layer_num, datatype) 元组映射到层索引
   - 维护层名称用于文档
   - 可以保存/加载层映射

4. **Region (gds_utils/region.py)**：包装 KLayout 的 Region 对象进行多边形操作
   - 提供布尔运算（subtract, add, and, or, xor）
   - 工厂方法：`create_polygon()`、`create_rings()`、`polygon2ring()`
   - 在多边形级别处理倒角和缩放

5. **Frame (gds_utils/frame.py)**：表示多边形顶点和几何变换
   - 将顶点列表存储为 (x, y) 元组
   - 实现 `offset()` 用于扩展/收缩多边形
   - 实现倒角算法：`apply_arc_fillet()`、`apply_adaptive_fillet()`
   - 处理顶点方向（顺时针 vs 逆时针）

### 数据流

**配置 YAML → main.py → GDS → Cell → Region → Frame**

1. 用户提供 YAML 配置
2. main.py 解析配置并创建 GDS 对象
3. 对于配置中的每个形状：
   - 解析顶点并创建 Frame
   - 应用变换（偏移、倒角）
   - 从 Frame 创建 Region
   - 将 Region 添加到指定层的 Cell
4. GDS 将所有单元格保存到输出文件

### 关键概念

**顶点和方向：**
- 所有多边形必须具有逆时针顶点顺序
- Frame 通过 `ensure_counterclockwise()` 自动检查和纠正方向

**偏移（缩放）：**
- 正偏移向外扩展多边形
- 负偏移向内收缩多边形
- 通过平行边平移和交点计算实现

**倒角：**
- **圆弧倒角**：所有角的统一半径（或每个顶点的半径列表）
- **自适应倒角**：凸角和凹角使用不同半径
- 倒角在偏移变换之后应用
- 半径调整考虑 zoom 以保持一致外观

**环阵列：**
- 通过生成具有指定宽度和间距的同心多边形创建
- `ring_width` 和 `ring_space` 可以是：
  - 单个浮点数：所有环统一
  - 浮点数列表：每环值
  - 基于规则的元组：`[(start, end, value), ...]` 用于批量配置
- 每个环是布尔减法：outer_boundary - inner_boundary

**通孔/孔洞结构：**
- `polygon2ring()` 从内外偏移创建单个环
- 用于铝溅射和通孔工艺

### 配置系统

**YAML 结构：**
```yaml
global:
  dbu: 0.001              # 数据库单位（微米）
  fillet:
    interactive: false    # 自动处理倒角冲突
    precision: 0.01       # 圆弧近似精度

gds:
  output_file: "output.gds"
  cell_name: "TOP"
  default_layer: [1, 0]

shapes:
  - type: "polygon" | "rings" | "via"
    vertices: "x1,y1:x2,y2:..."
    layer: [layer_num, datatype]
    zoom: float or [outer, inner]  # 注意：zoom 参数格式
    fillet:
      type: "arc" | "adaptive"
      radius: float
      radii: [r1, r2, ...]  # 每个顶点的半径
```

**重要提示：** 在当前实现中，`zoom` 是单个数值（或 [outer, inner] 用于向后兼容，但只使用第一个值）。正值 = 扩展，负值 = 收缩。

### ring_width/ring_space 的字符串保持

Web GUI 在 web_gui/app.py 中使用 `ensure_string_values()` 将 `ring_width` 和 `ring_space` 作为字符串保持在 YAML 中。这很关键，因为这些字段可以包含像 `"[(1,4,2), (5,8,4)]"` 这样的 Python 表达式，必须在 main.py（第 187-267 行）中用 `ast.literal_eval()` 解析。

**规则格式：**
```yaml
ring_width: "[(1, 5, 3), (6, 11, 2)]"
# 含义：环 1-5 宽度为 3，环 6-11 宽度为 2
```

## 重要实现细节

### 坐标系统
- 所有面向用户的坐标都以微米 (μm) 为单位
- 内部使用 `um_to_db()` 函数转换为数据库单位
- KLayout 使用整数数据库坐标

### 倒角边界情况
- 当倒角半径超过边长的一半时，代码会：
  - 抛出 ValueError（如果 > 最小边长的 80%）
  - 在交互模式下提示用户（如果 > 最小边长的 50%）
  - 自动缩小半径（如果 interactive=false 或用户选择选项 2）
- 零半径完全跳过倒角

### Region 布尔运算
- 通过运算符重载实现：`__sub__`、`__add__`、`__and__`、`__or__`、`__xor__`
- 包装 KLayout 的 Region 布尔方法
- 始终返回新的 Region 对象（不可变模式）

### 打包注意事项
- 使用 PyInstaller 创建独立可执行文件
- `getattr(sys, 'frozen', False)` 检测打包 vs 开发环境
- `sys._MEIPASS` 为打包资源提供临时目录
- Web GUI 使用 `get_base_path()` 和 `get_resource_path()` 进行路径解析

## 常见陷阱

1. **顶点顺序很重要**：操作前始终确保逆时针顺序
2. **先偏移后倒角**：操作顺序很关键 - 偏移在倒角之前进行
3. **环规则解析**：`ring_width`/`ring_space` 规则必须是有效的 Python 表达式
4. **层索引**：LayerManager 维护独立于 (layer_num, datatype) 的内部索引
5. **YAML 中的字符串类型**：使用规则语法时 ring_width/ring_space 必须是字符串

## 测试策略

测试位于 `tests/` 目录：
- `test_frame.py`：Frame 类方法（偏移、倒角、顶点操作）
- `test_region.py`：Region 布尔运算和多边形创建
- `test_gds_export.py`：端到端 GDS 文件生成
- `test_gds_utils.py`：工具函数测试

## 日志记录

日志通过 `gds_utils/utils.py` 配置：
- 使用 `logger.info()`、`logger.debug()`、`logger.error()`、`logger.warning()`
- 调用 `setup_logging(True)` 启用控制台输出
- 调试模式显示详细的顶点变换和操作步骤

## 开发规范

### 通用规则
- **语言**: 永远使用简体中文进行对话和文档，包括文档标题
- **文件大小**: Python文件尽可能不超过300行
- **虚拟环境**: 使用 `.venv` 目录名
- **包管理**: 使用uv进行依赖管理

### 架构约束
- **模块化设计**: 保持 `gds_utils/` 核心模块的独立性，避免循环依赖
- **前后端分离**: Web GUI代码放在 `web_gui/` 目录，与核心逻辑解耦
- **示例参考**: `examples/` 目录包含各类配置示例，新功能要提供对应示例
- **渐进式开发**: 功能分阶段实现，每阶段都要有测试验证
- **兼容性**: 代码和库的选型必须考虑跨平台兼容性（macOS, Linux, Windows）

### 测试和调试
- **单元测试**: 所有核心功能都要有对应的测试用例在 `tests/` 目录
- **日志记录**: 使用 `gds_utils/utils.py` 中的logger，合理使用不同日志级别
- **配置文件测试**: 新功能要提供YAML配置示例并验证可用性
- **文档同步**: 功能变更后及时更新 `docs/` 目录下的相关文档

### 代码风格
- **命名**: 使用中文注释，变量名和函数名使用英文
- **类型提示**: 关键函数使用类型标注（如 `Union[float, List[float]]`）
- **错误处理**: 使用try-except捕获异常，通过logger记录详细错误信息
- **向后兼容**: 修改现有功能时保持配置文件格式向后兼容
