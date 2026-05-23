# YAML Protocol v2

## 1. 目标

YAML 是 Summer GDS 的正式输入协议，面向 GUI、CLI 和自动化脚本。

协议只描述用户可见的业务对象：

- `base_shape`
- `via`
- `rings`

内部的 inner/outer、offset temporary、boolean temporary、operation graph 不进入 YAML。

## 2. 顶层结构

```yaml
schema_version: 2

global:
  unit: um
  dbu: 0.001

gds:
  top_cell: TOP
  output: build/example.gds

shapes:
  - type: base_shape
    sid: 0
    name: source_pad
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `schema_version` | 是 | 当前固定为 `2`。 |
| `global.unit` | 是 | 坐标单位，第一版固定建议 `um`。 |
| `global.dbu` | 是 | GDS database unit，单位为 `um`。 |
| `gds.top_cell` | 条件必填 | GDS 顶层 cell 名称。仅在输出 GDS 时必填。 |
| `gds.output` | 条件必填 | 默认 GDS 输出文件路径。仅在 `export --format gds`、CLI 未传 `--out` 且不是协议级 `validate` 时必填。 |
| `shapes` | 是 | 公开输出对象列表。 |

`gds` 只配置 GDS backend 默认值。

GUI 产品层只暴露 YAML 保存/加载和 GDS 导出。实时 SVG 预览由 GUI app service 写入程序内部临时目录并读回，不进入 YAML，也不作为用户导出产物。

CLI 或开发测试仍可直接选择 image renderer backend：

```bash
summer-gds export config.yaml --format svg --out build/preview.svg
summer-gds export config.yaml --format gds --out build/layout.gds
```

不要在 YAML 中增加 `outputs` 字段。YAML 中的 `shapes` 仍然全部是公开输出对象，`--format` 只决定这些对象导出成哪种 artifact。

注意：

- `validate config.yaml` 不要求 `gds.output`，因为它不选择 output backend。
- `export --format gds --dry-run` 要求能解析出最终 GDS 输出路径。
- `export --format svg --out preview.svg` 不读取也不要求 `gds.output`。
- GUI 导出 GDS 时，保存对话框选择的路径优先于 `gds.output`。
- 输出路径的解析、后缀、覆盖和 atomic write 规则定义在 CLI 契约中。

不支持字段：

- `outputs`
- `output.enabled`
- 用户显式定义的 `inner`
- 用户显式定义的 `outer`

## 3. ID 约定

### 3.1 sid

`sid` 是 shape id：

- 整数。
- 全局唯一。
- GUI 应自动递增生成，例如 `0, 1, 2, 3`。
- 删除 shape 后不要求重排已有 `sid`。
- 引用必须使用 `sid`，不能使用 `name`。

示例：

```yaml
- type: base_shape
  sid: 0
  name: source_pad
```

### 3.2 name

`name` 是人类可读名称：

- 不要求全局唯一。
- 不作为引用键。
- 可用于日志、GUI 展示、debug 文件名。

### 3.3 其它 ID 命名

后续对象如果需要 ID，应使用不同字段名，避免和 `sid` 混用：

| 字段 | 语义 |
| --- | --- |
| `sid` | shape id |
| `cid` | corner id |
| `oid` | operation id |
| `rid` | region/debug result id |

第一版 YAML 不要求暴露 `cid`、`oid`、`rid`。

## 4. Source 协议

所有 shape 都使用统一 `source` 字段。

### 4.1 顶点 source

```yaml
source:
  vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
```

要求：

- 坐标使用二维数组。
- 后端协议不使用 `"x,y; x,y"` 这类字符串格式。
- 顶点按边界顺序排列。
- 第一版不要求在 YAML 中显式闭合首尾点。

### 4.2 引用 source

```yaml
source:
  ref: 0
```

含义：

- 引用 `sid: 0` 的 canonical boundary。
- 不引用已经 boolean 后的多连通 Region。
- 第一版要求 `ref` 指向前面已经定义的 shape，避免 forward reference 和复杂 cycle 检测。

### 4.3 引用并 offset

```yaml
source:
  ref: 0
  offset: 10
```

含义：

- 取 `sid: 0` 的 canonical boundary。
- 先转为 Region。
- 执行 offset。
- 再转回单连通 BoundaryObject。
- 后续可以继续倒角和输出。

注意：

- `offset` 必须在倒角前完成。
- 如果 offset 后得到空 Region 或多个边界，第一版应报错。
- 对 `base_shape` 也支持 `source.ref + offset`。

## 5. base_shape

### 5.1 从顶点定义

```yaml
- type: base_shape
  sid: 0
  name: source_pad
  layer: [1, 0]
  source:
    vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
  fillet:
    radius: 2
```

处理流程：

```text
vertices -> BoundaryObject -> fillet -> RegionObject -> output backend
```

### 5.2 从已有图形 offset 定义

```yaml
- type: base_shape
  sid: 1
  name: source_pad_margin
  layer: [2, 0]
  source:
    ref: 0
    offset: 10
  fillet:
    radius: 2
```

处理流程：

```text
ref boundary -> RegionObject -> offset -> BoundaryObject -> fillet -> RegionObject -> output backend
```

## 6. via

```yaml
- type: via
  sid: 2
  name: contact_window
  layer: [10, 0]
  source:
    ref: 0
  offsets:
    inner: -5
    outer: 8
  fillet:
    inner:
      radius: 1
    outer:
      radius: 2
```

处理流程：

```text
source boundary
  -> inner offset -> inner boundary -> inner fillet -> inner region
  -> outer offset -> outer boundary -> outer fillet -> outer region
  -> outer region - inner region
  -> output backend
```

约束：

- `inner` 和 `outer` 都基于同一个 canonical source。
- 倒角在 boolean 前完成。
- boolean 后不再回到 BoundaryObject。
- 第一版只要求 boolean 结果非空。

## 7. rings

```yaml
- type: rings
  sid: 3
  name: guard_rings
  layer: [20, 0]
  source:
    ref: 0
  count: 3
  pitch: 12
  width: 4
  fillet:
    rings:
      - inner: { radius: 1 }
        outer: { radius: 2 }
      - inner: { radius: 1 }
        outer: { radius: 2 }
      - inner: { radius: 1 }
        outer: { radius: 2 }
```

推荐语义：

- `count` 是 ring 数量。
- `width` 是每圈 ring 宽度。
- `pitch` 是相邻 ring 同侧边界之间的距离。
- 第 `i` 圈基于源图形按迭代 offset 生成。

一种等价实现：

```text
ring_0_inner_offset = 0
ring_0_outer_offset = width

ring_i_inner_offset = i * pitch
ring_i_outer_offset = i * pitch + width
```

如果需要从内缩开始，可以在 `source` 上先使用负 offset 的 base_shape，再引用该 shape。

这会让该 offset base_shape 也作为公开 shape 输出。第一版不提供 internal/helper shape，也不提供 `outputs` 字段。

如果用户不希望该辅助层进入生产版图，推荐先使用 layer/datatype 约定隔离，例如把辅助 base_shape 放到 GUI/检查专用 layer；真正的 internal helper shape 留到后续版本单独设计。

处理流程：

```text
source boundary
  -> ring_0 inner/outer offset -> fillet -> boolean -> region
  -> ring_1 inner/outer offset -> fillet -> boolean -> region
  -> ring_2 inner/outer offset -> fillet -> boolean -> region
  -> output backend receives list[RegionObject]
```

第一版约束：

- 不暴露每一圈 inner/outer 到 YAML。
- 不要求 merge 成单个 Region。
- 不做 rings array 合并后的 holes 数量校验。
- 每圈 ring 的 boolean 结果必须非空。
- `fillet.rings` 可以省略。
- 如果提供 `fillet.rings`，长度必须等于 `count`。
- 如果所有 ring 使用相同倒角，用户应在 GUI 或生成器侧展开为长度等于 `count` 的列表；后端第一版不做隐式广播。

## 8. 完整示例

```yaml
schema_version: 2

global:
  unit: um
  dbu: 0.001

gds:
  top_cell: TOP
  output: build/layout.gds

shapes:
  - type: base_shape
    sid: 0
    name: source_pad
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
    fillet:
      radius: 2

  - type: base_shape
    sid: 1
    name: source_pad_margin
    layer: [2, 0]
    source:
      ref: 0
      offset: 10
    fillet:
      radius: 2

  - type: via
    sid: 2
    name: contact_window
    layer: [10, 0]
    source:
      ref: 0
    offsets:
      inner: -5
      outer: 8
    fillet:
      inner: { radius: 1 }
      outer: { radius: 2 }

  - type: rings
    sid: 3
    name: guard_rings
    layer: [20, 0]
    source:
      ref: 0
    count: 3
    pitch: 12
    width: 4
    fillet:
      rings:
        - inner: { radius: 1 }
          outer: { radius: 2 }
        - inner: { radius: 1 }
          outer: { radius: 2 }
        - inner: { radius: 1 }
          outer: { radius: 2 }
```

## 9. 版本兼容策略

第一版实现只需要支持 `schema_version: 2`。

如果需要兼容历史 YAML，应通过显式迁移脚本完成，而不是在主 parser 中长期保留多套隐式语义。
