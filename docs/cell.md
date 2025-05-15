# gds_utils.cell

## Cell 类

封装 KLayout 的 Cell，管理 LayerManager 和 Region。

### 构造方法

```python
Cell(kdb_cell: KLayoutDbCell)
```
[查看源码](../gds_utils/cell.py#L4)

### 方法

#### get_layer_index(self, layer_info: tuple[int, int]) -> int | None
获取图层索引。
[查看源码](../gds_utils/cell.py#L17)

#### create_layer(self, layer_info: tuple[int, int], layer_name: str = None) -> int
创建新图层。
[查看源码](../gds_utils/cell.py#L28)

#### add_region(self, region: Region, layer_info: tuple[int, int]) -> None
将 Region 添加到指定图层。
[查看源码](../gds_utils/cell.py#L56)

#### get_layer_manager(self) -> LayerManager
获取 LayerManager 实例。
[查看源码](../gds_utils/cell.py#L87) 