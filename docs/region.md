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
def create_polygon(cls, frame: Frame, fillet_config: dict = None, zoom_config: list = [0, 0]) -> 'Region'
```

参数：
- `frame`: Frame对象，包含多边形的顶点
- `fillet_config`: 倒角配置字典，可选
  ```python
  {
      "type": "arc",  # 或 "adaptive"
      "radius": 1.0,  # 倒角半径
      "precision": 0.01,  # 精度
      "interactive": False  # 是否交互式
  }
  ```
- `zoom_config`: 缩放配置，格式为 [外径缩放, 内径缩放]，可选
  - 外径缩放：正值向外扩展，负值向内收缩
  - 内径缩放：正值向外扩展，负值向内收缩

返回：
- Region 对象

### create_rings

从 Frame 对象创建环阵列。

```python
@classmethod
def create_rings(cls, initial_frame: Frame, ring_width: float, ring_space: float, ring_num: int, 
                fillet_config: dict = None, zoom_config: list = [0, 0]) -> 'Region'
```

参数：
- `initial_frame`: 初始 Frame 对象
- `ring_width`: 环宽度
- `ring_space`: 环间距
- `ring_num`: 环数量
- `fillet_config`: 倒角配置字典，可选
  ```python
  {
      "type": "arc",  # 或 "adaptive"
      "radius": 1.0,  # 倒角半径
      "precision": 0.01,  # 精度
      "interactive": False  # 是否交互式
  }
  ```
- `zoom_config`: 缩放配置，格式为 [外径缩放, 内径缩放]，可选
  - 外径缩放：控制所有环的外边界缩放
  - 内径缩放：控制所有环的内边界缩放

返回：
- Region 对象，包含所有环

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
    zoom_config=[1, 0]
)

# 创建环阵列
rings = Region.create_rings(
    frame,
    ring_width=1,
    ring_space=1,
    ring_num=3,
    fillet_config={"type": "arc", "radius": 1},
    zoom_config=[1, -1]
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

#### create_rings(cls, initial_frame: Frame, ring_width: float, ring_space: float, ring_num: int, fillet_config: dict = None) -> Region
从 Frame 创建多个环形 Region，可选倒角。
- **参数**
  - `initial_frame`: 初始 Frame。
  - `ring_width`: 环宽度。
  - `ring_space`: 环间距。
  - `ring_num`: 环数量。
  - `fillet_config`: 倒角配置字典。
- **返回**
  - Region 实例。
[查看源码](../gds_utils/region.py#L163)

#### 布尔运算符重载
- `__add__`, `__sub__`, `__and__`, `__or__`, `__xor__`
  - 支持 Region 之间的并、差、交、异或操作，返回新的 Region。
[查看源码](../gds_utils/region.py#L22) 