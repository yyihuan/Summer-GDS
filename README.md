# Summer-GDS

送给我最爱的夏夏~ 希望可以帮助她更加轻松地工作 ❤️

## 项目背景

这是一个基于Python的GDS文件生成工具，专门用于处理多边形和环阵列的生成。通过简单的配置文件，您可以轻松地创建各种复杂的GDS图形，包括基础多边形、环阵列等，并支持倒角和缩放功能。

## 功能特点

- 支持从顶点列表或生成配置创建多边形
- 支持创建多层环阵列
- 支持圆弧倒角和自适应倒角
- 支持内外边界的独立缩放
- 支持YAML格式的配置文件
- 支持图层映射和自定义

## 项目结构

```
Summer-GDS/
├── main_oop.py          # 主程序入口
├── config.yaml          # 配置文件示例
├── gds_utils/          # 核心工具包
│   ├── __init__.py
│   ├── frame.py        # Frame类，处理多边形顶点
│   ├── region.py       # Region类，处理GDS区域
│   ├── gds.py          # GDS类，处理GDS文件操作
│   └── utils.py        # 工具函数
└── README.md           # 项目文档
```

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

缩放功能通过 `zoom` 参数控制，格式为 `[外径缩放, 内径缩放]`：

- 外径缩放：控制形状外部的缩放
  - 正值：向外扩展
  - 负值：向内收缩
  - 0：不缩放

- 内径缩放：控制形状内部的缩放
  - 正值：向外扩展
  - 负值：向内收缩
  - 0：不缩放

例如：
- `[1, 0]`: 只对外部进行1微米的扩展
- `[0, -1]`: 只对内部进行1微米的收缩
- `[1, -1]`: 外部扩展1微米，内部收缩1微米

## 使用方法

1. 准备配置文件（参考 `config.yaml`）
2. 运行程序：
```bash
python main_oop.py config.yaml
```

## 注意事项

1. 确保顶点坐标按逆时针顺序排列
2. 倒角半径不应超过边长的一半
3. 缩放值应根据实际需求合理设置
4. 建议先使用小规模数据测试配置 