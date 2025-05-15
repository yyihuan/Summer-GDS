# main_oop.py

## 主要函数

### _generate_vertices(gen_config: dict) -> list[tuple[float, float]]
根据配置生成顶点列表。支持 `star` 等类型。
- **参数**
  - `gen_config`: 生成顶点的配置字典。
- **返回**
  - 顶点列表。
[查看源码](../main_oop.py#L8)

### parse_vertices(vertices_str: str) -> list[tuple[float, float]]
解析字符串格式的顶点列表。
- **参数**
  - `vertices_str`: 形如 "x1,y1:x2,y2:..." 的字符串。
- **返回**
  - 顶点列表。
[查看源码](../main_oop.py#L38)

### main()
主程序入口。解析 YAML 配置，驱动 GDS 生成流程。
[查看源码](../main_oop.py#L57) 