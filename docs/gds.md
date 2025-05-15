# gds_utils.gds

## GDS 类

封装 KLayout 的 Layout，管理 Cell 和 GDS 文件读写。

### 构造方法

```python
GDS(input_file: str = None, cell_name: str = "TOP", layer_info: tuple[int, int] = (1, 0), dbu: float = 0.001)
```
[查看源码](../gds_utils/gds.py#L5)

### 方法

#### save(self, output_file: str, save_layer_mapping_file: str = None) -> None
保存 GDS 文件，可选保存 layer mapping。
[查看源码](../gds_utils/gds.py#L97)

#### get_cells(self) -> list[Cell]
返回所有 Cell。
[查看源码](../gds_utils/gds.py#L56)

#### get_cell(self, cell_name: str) -> Cell | None
获取指定名称的 Cell。
[查看源码](../gds_utils/gds.py#L64)

#### create_cell(self, cell_name: str) -> Cell
创建新 Cell。
[查看源码](../gds_utils/gds.py#L75)

#### kdb_layout
直接访问 KLayout Layout 实例。
[查看源码](../gds_utils/gds.py#L5) 