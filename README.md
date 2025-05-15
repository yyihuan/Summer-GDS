# Summer GDS

基于 KLayout 的 GDS 文件生成工具，支持多边形和环形阵列的创建与操作。

## 功能特点

- 多边形生成，支持倒角功能
- 环形阵列生成，可自定义宽度和间距
- 多种形状支持（正方形、六边形、五角星、圆形）
- YAML 配置文件支持
- 图层管理
- GDS 文件导出

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

1. 创建 YAML 配置文件（例如 `config.yaml`）：

```yaml
global:
  dbu: 0.001
  fillet:
    interactive: true
  layer_mapping:
    save: true
    file: layer_mapping.txt

gds:
  input_file: null
  cell_name: TOP
  default_layer: [1, 0]
  output_file: output.gds

shapes:
  - name: star1
    type: polygon
    vertices_gen:
      shape_type: star
      center_x: 0
      center_y: 0
      outer_radius: 10
      inner_radius: 5
      points: 5
    layer: [10, 0]
    fillet:
      type: arc
      radius: 1
      precision: 0.01
      interactive: false
```

2. 运行脚本：

```bash
python main_oop.py config.yaml
```

## 文档

详细文档请参见 `docs` 目录。

## 许可证

MIT License 