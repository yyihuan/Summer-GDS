# Fillet Test Design

## 1. 目标

倒角测试负责验证单连通 BoundaryObject 上的圆弧倒角行为。

在完整产品流水线中，倒角的位置固定为：

```text
offset -> BoundaryObject -> fillet -> RegionObject -> boolean
```

因此测试必须覆盖两类场景：

- 直接来自 YAML vertices 的 BoundaryObject。
- 来自 Region offset 后再转回的 BoundaryObject。

不能只测原始 vertices，否则会漏掉 base offset、via、rings 的真实输入形态。

## 2. 当前算法边界

当前 MVP 圆弧倒角能力：

- 支持 polygon。
- 支持凸角和凹角。
- 共线角正半径应拒绝。
- 输入可归一化为 CCW，并同步映射用户半径。
- 未指定 `precision` 时使用默认策略：
  - `radius <= 20um` 使用 `0.001um`
  - `radius > 20um` 使用 `0.01um`
- 最大每角弧线采样数应有限制，避免顶点爆炸。

circle 不参与完整产品的 via/rings 倒角主线；如果保留 circle，应继续禁止 circle fillet。

## 3. 倒角输入对象

倒角函数推荐签名：

```python
def fillet_boundary(boundary: BoundaryObject, spec: FilletSpec) -> BoundaryObject:
    ...
```

不推荐：

```python
def fillet_points(points: list[tuple[float, float]], radii: list[float]) -> list[tuple[float, float]]:
    ...
```

原因：

- 裸数组缺少 owner、role、source_sid 等 metadata。
- via/rings 的 inner/outer 需要在错误信息中定位。
- offset 后的点序和数量可能不同于原始 YAML vertices。

## 4. Corner Metadata

长期方向上，每个角应有内部 corner object。

推荐字段：

| 字段 | 说明 |
| --- | --- |
| `cid` | corner id。 |
| `owner_sid` | 所属 shape。 |
| `role` | `base`、`via_inner`、`via_outer`、`ring_inner`、`ring_outer`。 |
| `user_index` | 如果来自 YAML vertices，对应原始顶点序号。 |
| `normalized_index` | 几何归一化后的内部序号。 |
| `prev_point` | 前一点。 |
| `vertex` | 当前角点。 |
| `next_point` | 后一点。 |
| `corner_kind` | `convex`、`concave`、`collinear`，内部派生。 |
| `radius` | 最终使用半径。 |
| `precision` | 最终使用精度。 |

第一版可以不把 `cid` 暴露到 YAML，但测试中的错误和 debug 信息应尽量保留角上下文。

## 5. 必测矩阵

### 5.1 基础倒角

| case | 目的 |
| --- | --- |
| rectangle uniform radius | 标准凸角。 |
| rectangle mixed radius | 混合半径和零半径。 |
| arrow concave | 凹角小圆弧。 |
| star concave/convex | 凸凹混合。 |
| sharp convex | 极尖锐凸角。 |
| collinear positive radius | 共线角正半径拒绝。 |
| radius too large | 切线距离超过边长拒绝。 |
| explicit precision | 用户精度覆盖默认精度。 |

### 5.2 offset 后倒角

| case | 目的 |
| --- | --- |
| base_ref_offset_then_fillet | base_shape offset 后倒角。 |
| via_inner_offset_then_fillet | via inner 边界倒角。 |
| via_outer_offset_then_fillet | via outer 边界倒角。 |
| ring_inner_offset_then_fillet | ring inner 边界倒角。 |
| ring_outer_offset_then_fillet | ring outer 边界倒角。 |

关键断言：

- fillet 输入点来自 offset 结果。
- 半径数量按 offset 后的边界点数校验。
- fillet 之后才转 RegionObject。
- boolean 操作拿到的是已经倒角后的 inner/outer RegionObject。

## 6. 几何断言

每个 corner 至少断言：

- `corner_kind` 正确。
- `radius` 正确映射到当前角。
- 零半径角保留原点。
- 正半径角生成两个切点和小圆弧。
- 切点落在相邻边上。
- 圆心到两个切点距离等于 radius。
- 输出 BoundaryObject 不自交。
- 输出面积为正。

对于凹角：

- 弧线必须是切点之间的小圆弧。
- 不允许绕成大圆弧。
- 不允许穿越原边界外的错误区域。

## 7. 错误路径

直接 vertices 输入时，错误可指向：

```text
$.shapes[0].fillet.radii[2]
```

via/rings 的内部边界错误应指向对应配置：

```text
$.shapes[2].fillet.inner.radius
$.shapes[3].fillet.rings[1].outer.radius
```

如果错误来自 offset 后新增或变化的角，path 可以指向 shape 或 fillet object，同时在 detail 中携带：

```json
{
  "stage": "fillet",
  "role": "ring_outer",
  "ring_index": 1,
  "normalized_index": 7
}
```

## 8. PNG 可视化

PNG 检查项：

- 原始或 offset 后边界。
- 倒角后边界。
- 圆弧采样点。
- via/rings boolean 后填充区域。

建议每张 debug PNG 使用不同颜色：

- source boundary：灰色线。
- offset boundary：蓝色线。
- filleted boundary：橙色线。
- final region：半透明填充。

PNG 只用于人工检查，不替代几何断言。

## 9. 与完整流水线的关系

倒角模块不理解：

- YAML 顶层结构。
- source.ref 解析。
- Region boolean。
- GDS writer。

倒角模块只做：

```text
BoundaryObject + FilletSpec -> BoundaryObject
```

这保证 base、via、rings 可以复用同一倒角实现。
