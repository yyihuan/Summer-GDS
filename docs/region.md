# gds_utils.region

## Region 类

封装 KLayout 的 Region 对象，支持多边形/环的创建与布尔运算。

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