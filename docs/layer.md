# gds_utils.layer

## LayerManager 类

管理图层名称与 KLayout 图层索引的映射。

### 构造方法

```python
LayerManager()
```
[查看源码](../gds_utils/layer.py#L3)

### 方法

#### get_layer_index(self, layer_info: tuple[int, int]) -> int | None
获取图层索引。
[查看源码](../gds_utils/layer.py#L12)

#### create_layer(self, layer_info: tuple[int, int], layer_name: str = None) -> int
创建新图层，返回索引。
[查看源码](../gds_utils/layer.py#L23)

#### get_layer_name(self, layer_info: tuple[int, int]) -> str | None
获取图层名称。
[查看源码](../gds_utils/layer.py#L54)

#### get_all_layers(self) -> dict
返回所有图层信息。
[查看源码](../gds_utils/layer.py#L65)

#### save_mapping(self, output_file: str) -> None
保存图层映射到文件。
[查看源码](../gds_utils/layer.py#L74)

#### load_mapping(self, input_file: str) -> None
从文件加载图层映射。
[查看源码](../gds_utils/layer.py#L96) 