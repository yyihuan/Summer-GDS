# 独立倒角半径功能使用指南

Summer-GDS支持为多边形的每个角设置不同的倒角半径，这使得您可以更加灵活地控制多边形的形状。

## 配置方法

在多边形或环阵列的配置中，您可以通过`fillet.radii`参数指定每个角的倒角半径：

```yaml
fillet:
  type: "arc"
  radius: 1  # 默认半径，当半径列表长度不匹配顶点数时使用
  radii: [2, 0.5, 1.5, 1]  # 每个角的半径，按顶点顺序
  precision: 0.01
  interactive: false
```

## 参数说明

- `radius`: 默认倒角半径，当未提供`radii`或`radii`长度不足时使用
- `radii`: 倒角半径列表，按顶点顺序应用于多边形的每个角
  - 列表中的值必须是数字
  - 值为0的角不会进行倒角处理
  - 如果列表长度小于顶点数，将使用`radius`作为默认值

## 示例

### 1. 正方形每个角使用不同的倒角半径

```yaml
- type: "polygon"
  name: "Variable_Fillet_Square"
  vertices: "0,0:10,0:10,10:0,10"
  layer: [1, 0]
  fillet:
    type: "arc"
    radius: 1
    radii: [2, 0.5, 1.5, 1]  # 四个角分别使用2, 0.5, 1.5, 1的倒角半径
    precision: 0.01
    interactive: false
```

### 2. 部分角不倒角

```yaml
- type: "polygon"
  name: "Partial_Fillet_Square"
  vertices: "0,0:10,0:10,10:0,10"
  layer: [2, 0]
  fillet:
    type: "arc"
    radius: 1
    radii: [2, 0, 1.5, 0]  # 第二和第四个角不倒角
    precision: 0.01
    interactive: false
```

### 3. 五角星交替倒角

```yaml
- type: "polygon"
  name: "Star_Variable_Fillet"
  vertices_gen:
    shape_type: "star"
    center_x: 50
    center_y: 50
    outer_radius: 15
    inner_radius: 7
    points: 5
  layer: [3, 0]
  fillet:
    type: "arc"
    radius: 0.5
    radii: [2, 0, 1.5, 0, 1.5, 0, 1.5, 0, 1.5, 0]  # 尖角不倒角，其他角使用不同半径
    precision: 0.01
    interactive: false
```

## Web GUI支持

在Web GUI界面中，您可以通过以下步骤设置独立倒角半径：

1. 创建一个多边形或环阵列
2. 在倒角半径输入框旁边点击"切换到半径列表"按钮
3. 在出现的文本框中输入以逗号分隔的半径值列表
4. 如需切换回单一半径模式，点击"切换到单一半径"按钮

## 注意事项

1. 确保倒角半径不超过相邻边长的一半，否则可能导致倒角失败
2. 当使用半径列表时，请确保顶点顺序正确，因为半径值将按顶点顺序应用
3. 对于环阵列，内外边界的倒角半径列表应分别设置，但目前两者使用相同的列表
4. 值为0的角不会进行倒角处理，可以利用这一点来选择性地倒角 