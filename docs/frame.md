# gds_utils.frame

## Frame 类

用于表示和操作多边形顶点序列，支持顺/逆时针判断、偏移、倒角等操作。

### 构造方法

```python
Frame(vertices: list[tuple[float, float]])
```
- **参数**  
  - `vertices`: 多边形顶点列表，格式为 `[(x1, y1), (x2, y2), ...]`。
[查看源码](../gds_utils/frame.py#L5)

---

### 方法

#### is_clockwise(self) -> bool
判断当前多边形顶点顺序是否为顺时针。
[查看源码](../gds_utils/frame.py#L8)

#### ensure_counterclockwise(self) -> None
确保多边形顶点为逆时针顺序（如为顺时针则反转）。
[查看源码](../gds_utils/frame.py#L18)

#### offset(self, width: float) -> Frame
生成偏移后的新 Frame。  
- **参数**  
  - `width`: 偏移宽度，正值为外扩，负值为内缩（当前仅支持外扩）。
- **返回**  
  - 新的 Frame 实例。
[查看源码](../gds_utils/frame.py#L23)

#### get_vertices(self) -> list[tuple[float, float]]
返回当前 Frame 的顶点列表。
[查看源码](../gds_utils/frame.py#L84)

#### is_convex_vertex(prev_point, curr_point, next_point) -> bool
静态方法，判断一个顶点是否为凸角。
[查看源码](../gds_utils/frame.py#L88)

#### line_intersection(line1, line2) -> tuple[float, float] | None
静态方法，计算两条线段的交点，平行时返回 None。
[查看源码](../gds_utils/frame.py#L96)

#### apply_arc_fillet(self, radius_or_radii_list, precision=0.01, interactive=True) -> Frame
对所有顶点应用圆弧倒角。  
- **参数**  
  - `radius_or_radii_list`: 单一半径或每个顶点的半径列表。
  - `precision`: 倒角精度。
  - `interactive`: 是否交互处理特殊情况。
- **返回**  
  - 新的 Frame 实例。
[查看源码](../gds_utils/frame.py#L149)

#### apply_adaptive_fillet(self, convex_radius, concave_radius, precision=0.01, interactive=True) -> Frame
根据顶点凹凸性自适应应用不同倒角半径。  
- **参数**  
  - `convex_radius`: 凸角倒角半径。
  - `concave_radius`: 凹角倒角半径。
  - `precision`: 倒角精度。
  - `interactive`: 是否交互处理特殊情况。
- **返回**  
  - 新的 Frame 实例。
[查看源码](../gds_utils/frame.py#L116) 