# 独立倒角半径功能使用指南

Summer-GDS 支持为多边形或环阵列的每个角设置独立的倒角半径，这使得您可以更加灵活地控制几何形状。同时，解析器会对输入进行严格校验，确保半径数量与顶点/环数一致，若不匹配则立即报错提示。

## 配置方法

在多边形或环阵列的配置中，推荐使用 `fillet.radius_list` 指定每个角的倒角半径；为兼容旧版，也接受 `fillet.radius`（单值）及 `fillet.radii`（同 `radius_list`）。

```yaml
fillet:
  type: "arc"
  radius: 1          # 单值写法，将在解析时自动扩展为与顶点数相同的列表
  radius_list: [2, 0.5, 1.5, 1]  # 每个角的半径，按顶点顺序
  precision: 0.01
  interactive: false
```

## 参数说明

- `radius`: 单一倒角半径写法，解析器会将其扩展成与顶点数相同的 `radius_list`
- `radius_list`（或旧写法 `radii`）：倒角半径列表，按顶点顺序应用
  - 列表中的值必须是数字
  - 值为 0 的角不会进行倒角处理
  - **长度必须与顶点数（或 `ring_num * 顶点数`）一致**，否则会抛出异常并终止流程

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
    radius_list: [2, 0.5, 1.5, 1]  # 四个角分别使用2, 0.5, 1.5, 1的倒角半径
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
    radius_list: [2, 0, 1.5, 0]  # 第二和第四个角不倒角
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
    radius_list: [2, 0, 1.5, 0, 1.5, 0, 1.5, 0, 1.5, 0]  # 尖角不倒角，其他角使用不同半径
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
3. 对于环阵列，结合 `ring_mode` 可实现三种常用模式：
   - `custom`：`radius_list` 长度等于顶点数时自动复制；等于 `ring_num * 顶点数` 时按圈取值。
   - `concentric`：所有环共享同一组半径，但会结合缩放参数计算偏移后的实际倒角。
4. 值为0的角不会进行倒角处理，可以利用这一点来选择性地倒角。
