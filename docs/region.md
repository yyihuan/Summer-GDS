# gds_utils.region

## Region 类

Region 类封装了 KLayout 的 Region 对象，用于创建和操作多边形区域。

## 主要功能

- 创建多边形区域
- 创建环阵列
- 支持布尔运算
- 支持倒角操作
- 支持缩放操作

## 方法说明

### create_polygon

从 Frame 对象创建多边形区域。

```python
@classmethod
def create_polygon(
    cls,
    frame: Frame,
    fillet_config: dict = None,
    zoom_config: Union[int, float] = 0,
) -> 'Region'
```

参数：
- `frame`: Frame对象，包含多边形的顶点
- `fillet_config`: 倒角配置字典，可选
  ```python
  {
      "type": "arc",  # 或 "adaptive"
      "radius"/"radius_list": 1.0,  # 倒角半径（单值或列表）
      "precision": 0.01,  # 精度
      "interactive": False  # 是否交互式
  }
  ```
- `zoom_config`: 单个缩放值（μm），对整体轮廓执行等距偏移；正值向外扩展，负值向内收缩

返回：
- Region 对象

### create_rings

从 Frame 对象创建环阵列。

```python
@classmethod
def create_rings(
    cls,
    initial_frame: Frame,
    ring_width: Union[float, List[float]],
    ring_space: Union[float, List[float]],
    ring_num: int,
    fillet_config: dict = None,
    zoom_config: Union[int, float] = 0,
    inner_zoom: Optional[Union[int, float]] = None,
    outer_zoom: Optional[Union[int, float]] = None,
    ring_radii_series: Optional[List[List[float]]] = None,
) -> 'Region'
```

参数：
- `initial_frame`: 初始 Frame 对象
- `ring_width`: 环宽度，单值或列表（列表长度需等于 `ring_num`）
- `ring_space`: 环间距，单值或列表（同上）
- `ring_num`: 环数量
- `fillet_config`: 倒角配置字典，可选，`radius_list` 将在需要时被逐环覆盖
- `zoom_config`: 整体缩放值（μm），作用于每一圈的基准偏移
- `inner_zoom` / `outer_zoom`: 对内/外边界额外施加的缩放（δ），允许独立控制环宽
- `ring_radii_series`: 可选的二维半径列表（长度为 `ring_num`），将对应覆盖每一圈的 `radius_list`

返回：
- Region 对象，包含所有环

> 提示：CLI 中可以通过 `ring_mode` 与 `fillet.radius_list` 搭配生成 `ring_radii_series`。

#### 环倒角模式（CLI/YAML）

在 `shapes` 配置中新增的 `ring_mode` 字段用于描述半径列表如何应用到每一圈：

- `custom`（默认）：
  - 若 `fillet.radius_list` 长度等于顶点数，则自动复制到每一圈。
  - 若长度等于 `ring_num * 顶点数`，则按顺序切片，允许每圈独立设置倒角半径。
  - 不会根据环宽/间距对半径做缩放修正，完全尊重用户输入。
- `concentric`：要求 `fillet.radius_list` 长度等于顶点数。所有环共享同一组半径，但会结合 `ring_width`/`ring_space` 及缩放参数计算出同心偏移后的实际倒角半径。

配置异常（如列表长度不匹配、出现负值）会触发异常并终止流程，以避免产生不可预期的几何结果。

### 布尔运算

Region 类支持以下布尔运算：

- `__sub__`: 减法运算
- `__add__`: 加法运算（合并）
- `__and__`: 与运算（交集）
- `__or__`: 或运算（合并）
- `__xor__`: 异或运算

## 使用示例

```python
# 创建基础多边形
frame = Frame([(0,0), (10,0), (10,10), (0,10)])
region = Region.create_polygon(
    frame,
    fillet_config={"type": "arc", "radius": 1},
    zoom_config=1
)

# 创建环阵列
rings = Region.create_rings(
    frame,
    ring_width=1,
    ring_space=1,
    ring_num=3,
    fillet_config={"type": "arc", "radius": 1},
    zoom_config=1,
    inner_zoom=-1,
    outer_zoom=1
)
```

### 构造方法

```python
Region()
```
- 创建一个空 Region。
[查看源码](../gds_utils/region.py#L6)

---

### 方法

#### get_klayout_region(self) -> db.Region
返回内部的 KLayout Region 对象。
[查看源码](../gds_utils/region.py#L14)

#### create_polygon(cls, frame: Frame, fillet_config: dict = None) -> Region
从 Frame 创建多边形 Region，可选倒角。
- **参数**
  - `frame`: Frame 实例。
  - `fillet_config`: 倒角配置字典，详见 README 示例。
- **返回**
  - Region 实例。
[查看源码](../gds_utils/region.py#L88)

#### create_rings(cls, initial_frame: Frame, ring_width: Union[float, List[float]], ring_space: Union[float, List[float]], ring_num: int, fillet_config: dict = None, zoom_config: Union[int, float] = 0, inner_zoom: Optional[Union[int, float]] = None, outer_zoom: Optional[Union[int, float]] = None, ring_radii_series: Optional[List[List[float]]] = None) -> Region
从 Frame 创建多个环形 Region，可选倒角。
- **参数**
  - `initial_frame`: 初始 Frame。
  - `ring_width`: 环宽度（单值或列表）。
  - `ring_space`: 环间距（单值或列表）。
  - `ring_num`: 环数量。
  - `fillet_config`: 倒角配置字典。
  - `zoom_config` / `inner_zoom` / `outer_zoom`: 缩放与内外边界增量。
  - `ring_radii_series`: 可选的逐圈半径列表，用于覆盖 `radius_list`。
- **返回**
  - Region 实例。
[查看源码](../gds_utils/region.py#L163)

#### 布尔运算符重载
- `__add__`, `__sub__`, `__and__`, `__or__`, `__xor__`
  - 支持 Region 之间的并、差、交、异或操作，返回新的 Region。
[查看源码](../gds_utils/region.py#L22) 
