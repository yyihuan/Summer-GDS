# Summer GDS Refactor PRD v2

## 1. 背景

Summer GDS 当前已经验证了核心几何能力：

- 可从 YAML 生成 GDS。
- 可对单连通边界做倒角。
- 可借助 KLayout 做基础 GDS 输出。

下一阶段目标不是继续在现有脚本上堆功能，而是把程序抽象成稳定流水线：

```text
YAML 业务对象 -> 编译为几何任务 -> KLayout Region 几何内核 -> output backend
```

其中 YAML 是 GUI、CLI、自动化脚本之间的正式协议。

## 2. 产品目标

### 2.1 必须支持的对象

第一版 refactor 需要支持三类公开输出对象：

- `base_shape`：基础多边形，可直接由顶点定义，也可从已有图形 offset 得到。
- `via`：由同一源图形生成 inner/outer，倒角后布尔相减得到单个带孔区域。
- `rings`：从源图形迭代生成多圈 ring，每圈倒角后布尔相减，最后作为多个 Region 输出。

### 2.2 必须支持的用户能力

- 用户可以通过 `sid` 引用已有图形。
- 用户可以用 `source.ref + offset` 定义新图形，避免手工重复计算坐标。
- 用户可以为不同对象配置 layer。
- 用户可以为 base、via、rings 分别配置倒角。
- GUI 用户通过图形类型选择、坐标/参数表单创建配置；GUI 自动生成 YAML，用户不需要直接手写 YAML。
- GUI 左侧主界面以 shape 列表为中心；Global 设置通过弹层/抽屉完成，YAML 只作为只读预览模式出现，不作为默认编辑面板。
- GUI 自动写入 `schema_version: 2`，不把 schema version 暴露为普通用户设置；打开旧版或缺失版本 YAML 时给出明确错误。
- GUI 导出 GDS 的路径由保存对话框决定；`gds.output` 只作为 CLI 兼容字段保留，不作为 GUI 导出路径输入。
- GUI 用户可以保存/加载 YAML，并把同一份几何结果导出为 GDS。
- GUI 用户可以看到实时 SVG 预览；SVG 是程序内部预览，不是用户导出产物。
- 用户不需要理解内部 inner/outer、DAG、Region 转换等实现细节。

### 2.3 非目标

第一版不做：

- GUI 远程服务化。
- 自研布尔几何内核。
- rings array merge 后的复杂拓扑校验。
- 任意多洞、多岛、多层级多连通对象的通用建模。
- 完整 DRC、最小间距、sliver 检测。

## 3. 核心原则

### 3.1 YAML 只表达业务对象

YAML 里的 `shapes` 都是公开输出对象。

内部过程对象不进入 YAML：

- inner boundary
- outer boundary
- offset temporary
- boolean temporary
- debug region

因此 YAML 中不需要 `outputs` 或 `output.enabled`。只要出现在 `shapes` 里，就会输出。

### 3.2 几何计算使用 KLayout Region

KLayout `Region` 是内部几何内核，用于：

- offset
- boolean
- GDS writer 和 image renderer 输入

但 Region 不是 YAML 协议对象。YAML 面向业务对象，程序内部再编译为 Region 流水线。

### 3.3 倒角必须在 boolean 前

正确顺序：

```text
source -> offset -> boundary -> fillet -> region -> boolean -> output backend
```

原因：

- 如果先倒角再 offset，offset 会改变倒角半径和边界精度。
- boolean 后得到的是 Region，多连通区域无法再按原始单连通边界做逐角倒角。
- via/ring 的 inner/outer 必须分别倒角后再 boolean。

### 3.4 Output backend 只接受 RegionObject

所有公开对象最终都统一成 `RegionObject` 进入 output backend：

```text
base_shape -> RegionObject
via        -> RegionObject
rings      -> list[RegionObject]
```

GDS writer 和 image renderer 不接收裸顶点、不接收 BoundaryObject、不接收业务对象。

## 4. 用户故事

### 4.1 基础图形

用户定义一个基础多边形：

```yaml
- type: base_shape
  sid: 0
  name: source_pad
  layer: [1, 0]
  source:
    vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
```

程序输出一个对应的 GDS polygon。

### 4.2 基于已有图形 offset

用户基于 `sid: 0` 生成外扩图形：

```yaml
- type: base_shape
  sid: 1
  name: source_pad_margin
  layer: [2, 0]
  source:
    ref: 0
    offset: 10
```

用户不需要重新计算外扩后的顶点。

### 4.3 Via

用户从一个源图形生成 via：

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
```

程序内部生成：

```text
outer_region - inner_region
```

最终输出单个 Region。

### 4.4 Rings

用户从一个源图形迭代生成多圈 ring。源图形可以是直接 `vertices`，也可以是已有 base_shape 的 `ref` / 可选 `offset`：

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
```

程序内部生成多个 ring region。第一版不要求把这些 region merge 成一个拓扑对象。

## 5. 成功标准

### 5.1 功能标准

- YAML v2 可以描述 base、via、rings。
- 所有对象最终统一进入 RegionObject output backend。
- base_shape 和 rings 支持 `vertices` 和 `ref + offset` 两种 source；via 只引用已有 base_shape。
- via 和 rings 的 offset、倒角、boolean 顺序正确。
- `sid` 引用稳定，不依赖 `name`。
- `export --format gds` 走统一几何流水线。
- GUI 实时 SVG 预览复用同一条几何流水线，但不暴露为用户导出产物。

### 5.2 工程标准

- YAML schema 和内部数据模型清晰分离。
- KLayout Region 只作为内部几何内核和 output backend 输入。
- 操作依赖由内部 execution graph 表达，不泄漏到 YAML。
- 每个流水线阶段产物类型明确。
- 测试覆盖 schema、offset、fillet、boolean、GDS writer、image renderer。

### 5.3 可维护性标准

- 文档按职责拆分。
- 图例能解释数据流和对象生命周期。
- 后续 GUI 只需要生成 YAML，不需要重复实现几何逻辑。
- 新对象类型可按同一编译流程加入。
