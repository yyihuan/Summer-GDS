# Summer-GDS

送给我最爱的夏夏~ 希望可以帮助她更加轻松地工作 ❤️

## 项目背景

这是一个基于Python的GDS文件生成工具，专门用于处理多边形和环阵列的生成。通过简单的配置文件，您可以轻松地创建各种复杂的GDS图形，包括基础多边形、环阵列、圆形等，并支持倒角和缩放功能。

## 功能特点

- 支持从顶点列表创建多边形
- ✨ **支持圆形定义**：通过圆心、半径、精度参数自动生成圆形
- 支持创建多层环阵列
- 支持圆弧倒角和自适应倒角
- 支持为多边形/环阵列的每个角设置不同的倒角半径
- 支持内外边界的独立缩放
- 支持YAML格式的配置文件
- 支持图层映射和自定义
- 提供Web GUI界面，支持可视化编辑

## 项目结构

```
Summer-GDS/
├── main.py              # 主程序入口（当前版本）
├── config.yaml          # 配置文件示例
├── gds_utils/           # 核心工具包
│   ├── __init__.py
│   ├── frame.py         # Frame类，处理多边形顶点
│   ├── region.py        # Region类，处理GDS区域
│   ├── gds.py           # GDS类，处理GDS文件操作
│   ├── cell.py          # Cell类，处理GDS单元格
│   ├── layer.py         # LayerManager类，处理图层管理
│   └── utils.py         # 工具函数
├── web_gui/             # Web图形界面
│   ├── app.py           # Flask应用
│   ├── run.py           # 启动脚本
│   ├── requirements.txt # Web GUI依赖
│   ├── templates/       # HTML模板
│   └── static/          # 静态资源
├── docs/                # 项目文档
│   ├── TODO.md          # 待办事项清单
│   └── fillet_radius_list.md
├── discuss/             # 技术讨论和方案
│   └── multi_shape_support/  # 圆形支持功能设计文档
├── examples/            # 配置示例
├── tests/               # 测试文件
├── CLAUDE.md            # Claude Code 项目指导文档
└── README.md
```

## Web GUI界面

Summer-GDS现在提供了一个友好的Web图形界面，方便您通过浏览器创建和编辑GDS配置文件。

### 使用方法

#### 方法一：使用启动脚本（推荐）

可以直接使用根目录下的启动脚本：

```bash
./start_web_gui.sh
```

支持的参数：
- `--host=IP地址`：指定服务器绑定的IP地址，默认为0.0.0.0（允许从任何IP访问）
- `--port=端口号`：指定服务器端口，默认为5000
- `--debug`：启用调试模式

例如：
```bash
./start_web_gui.sh --host=127.0.0.1 --port=8080 --debug
```

#### 方法二：手动启动

1. 进入web_gui目录：
```bash
cd web_gui
```

2. 安装Web GUI依赖：
```bash
pip install -r requirements.txt
```

3. 启动Web服务器：
```bash
python run.py
```

4. 打开浏览器访问：http://localhost:5001

### Web GUI功能

- ✨ **圆形支持**：可视化创建圆形，支持圆心、半径、精度参数设置
- 可视化创建和编辑多边形和环阵列
- 实时YAML和JSON编辑
- 一键生成和下载GDS文件
- 配置保存和加载
- 动态表单切换（顶点坐标 ↔ 圆形参数）

详细使用说明请参阅 [web_gui/README.md](web_gui/README.md)

## 配置说明

### 基础配置

```yaml
global:
  dbu: 0.001  # 数据库单位（微米）
  fillet:
    interactive: false  # 是否启用交互式选择
    default_action: "auto"  # 当interactive=false时的默认行为
    precision: 0.01  # 倒角精度（微米）

gds:
  input_file: null  # 输入GDS文件，null表示创建新文件
  output_file: "output.gds"
  cell_name: "TOP"  # 默认cell名称
  default_layer: [1, 0]  # 默认layer [layer_num, datatype]
```

### 形状配置

#### 基础多边形

```yaml
- type: "polygon"
  name: "Square"
  vertices: "0,0:10,0:10,10:0,10"  # 顶点坐标，格式：x1,y1:x2,y2:...
  layer: [1, 0]
  fillet:
    type: "arc"
    radius: 1
    precision: 0.01
    interactive: false
  zoom: [1, 0]  # [外径缩放, 内径缩放]
```

#### 圆形多边形（✨ 新功能）

```yaml
- type: "polygon"
  name: "Circle"
  # 圆形通过前端Web GUI生成，最终保存为顶点坐标
  vertices: "10.000,0.000:9.951,0.980:9.808,1.951:..."  # 自动生成的圆形顶点
  layer: [1, 0]
  fillet:
    type: "arc"
    radius: 0.5
  zoom: 0
```

##### 圆形精度参考表

圆形通过多边形顶点近似，精度参数决定顶点数量和近似误差：

| 精度值 | 顶点数 | 100μm圆误差 | 1000μm圆误差 | 视觉效果 | 推荐用途 |
|--------|--------|-------------|--------------|----------|----------|
| 32     | 32     | 0.38μm      | 3.8μm        | 一般     | 粗略图形、快速验证 |
| **64** | **64** | **0.098μm** | **0.98μm**   | **良好** | **一般应用（推荐）** |
| 128    | 128    | 0.024μm     | 0.244μm      | 很好     | 精密器件 |
| 256    | 256    | 0.006μm     | 0.061μm      | 极好     | 超高精度要求 |

**精度选择建议**：
- **日常使用**：64精度提供最佳的性能和精度平衡
- **精密应用**：当误差需要小于0.1μm时，选择128或更高精度
- **大型图形**：对于直径>10mm的圆形，64精度已足够
- **文件大小**：高精度会显著增加GDS文件大小和处理时间

#### 使用独立倒角半径的多边形

```yaml
- type: "polygon"
  name: "Variable_Fillet_Square"
  vertices: "0,0:10,0:10,10:0,10"
  layer: [1, 0]
  fillet:
    type: "arc"
    radius: 1  # 默认半径，当半径列表长度不匹配顶点数时使用
    radii: [2, 0.5, 1.5, 1]  # 每个角的半径，按顶点顺序
    precision: 0.01
    interactive: false
  zoom: [1, 0]
```

> 详细的独立倒角半径功能说明请参阅 [docs/fillet_radius_list.md](docs/fillet_radius_list.md)

#### 环阵列

```yaml
- type: "rings"
  name: "Square_Rings"
  vertices: "0,0:10,0:10,10:0,10"
  ring_width: 1    # 环宽度
  ring_space: 1    # 环间距
  ring_num: 3      # 环数量
  layer: [2, 0]
  fillet:
    type: "arc"
    radius: 1
    precision: 0.01
    interactive: false
  zoom: [1, -1]    # [外径缩放, 内径缩放]
```

### 缩放功能说明

缩放功能通过 `zoom` 参数控制：

**新版本格式（推荐）**：
- `zoom: 1.5`：向外扩展1.5微米
- `zoom: -0.5`：向内收缩0.5微米
- `zoom: 0`：不缩放

**传统格式（向后兼容）**：
- `zoom: [1, 0]`：只使用第一个值进行缩放
- `zoom: [外径, 内径]`：内径参数已弃用，仅保留向后兼容

## 使用方法

### 命令行模式
1. 准备配置文件（参考 `config.yaml`）
2. 运行程序：
```bash
python main.py config.yaml
```

### Web GUI模式（推荐）
1. 启动Web服务器：
```bash
./start_web_gui.sh
```
2. 打开浏览器访问：http://localhost:5000
3. 使用可视化界面创建圆形、多边形和环阵列
4. 一键生成和下载GDS文件

## 注意事项

1. 确保顶点坐标按逆时针顺序排列
2. 倒角半径不应超过边长的一半
3. 缩放值应根据实际需求合理设置
4. 建议先使用小规模数据测试配置
5. **圆形功能**：仅在Web GUI中可用，生成后保存为顶点坐标
6. **文档更新**：某些信息可能滞后，以实际代码实现为准

## 最新功能

### ✨ 圆形支持（✅ 已完成）
- 在Web GUI中支持圆形定义
- 自动生成圆形顶点坐标
- 支持圆心、半径、精度参数设置
- 提供精度误差参考表
- 适用于polygon和rings类型
- 支持圆形参数的保存和反向编辑
- 完整的元数据支持和配置兼容性

## 待开发功能

详细的待办事项清单请参阅：[docs/TODO.md](docs/TODO.md)

### 高优先级
1. **矩形生成器**：支持中心点+宽高的矩形定义
2. **椭圆生成器**：支持椭圆图形生成
3. **实时预览**：添加形状的可视化预览功能
4. **参数验证增强**：添加更严格的圆形参数验证
5. **圆形旋转角度**：为圆形/正多边形生成增加“旋转角度”参数，支持任意正多边形成角对齐

### 中优先级
1. **单文件多cell支持**：在同一GDS文件中管理多个cell
2. **多边形顶点导入**：从外部文件导入顶点坐标
3. **图层颜色映射**：支持图层的颜色显示
4. **更多形状生成器**：正多边形、扇形等 
