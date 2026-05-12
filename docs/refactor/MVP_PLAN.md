# Summer-GDS MVP 架构与实施方案

文档版本：v0.1
日期：2026-05-12
状态：MVP 设计稿

---

## 0. 结论

MVP 采用 **CLI-first + 严格 YAML v1 + 基础图形生成 + 倒角占位接口**。

这不是完整重构 v1，也不是继续在旧 `main.py` 上补兼容。MVP 的目标是先建立一个可信、可测试、可扩展的窄内核：

- 支持 `base_shape`：`polygon` 和 `circle`
- 支持 CLI：`validate` 和 `generate`
- 支持严格 YAML 解析器：拒绝模糊输入、未知字段和旧协议
- 支持最小倒角占位：`bevel` 直线切角
- 输出可被 KLayout 打开的 GDS
- 不承诺 fab 可用的圆弧倒角精度

推荐策略：**先把协议、验证、错误模型、生成管线做完整，再迭代几何能力**。这样后续加入 `rings`、`via`、新圆弧倒角、GUI 或旧 YAML 迁移器时，不需要重写核心管线。

---

## 1. 文档关系

现有文档仍作为长期目标参考：

| 文档 | 角色 |
|---|---|
| `PRD.md` | 长期产品目标，GUI 是主入口 |
| `technical-spec.md` | 长期技术规格，包含 rings/via/GUI/GDS reverse reader 等内容 |
| `yaml-protocol.md` | 长期 YAML 协议草案 |
| `MVP_PLAN.md` | 当前第一阶段唯一执行依据 |

MVP 与长期规格的差异：

| 主题 | 长期规格 | MVP |
|---|---|---|
| 主入口 | GUI | CLI |
| YAML 顶点 | `"x1,y1;x2,y2"` 字符串 | `[[x, y], ...]` 数值对列表 |
| 图形类型 | `base_shape` / `rings` / `via` | 仅 `base_shape` |
| 倒角 | 圆弧倒角，未来替换新方案 | `bevel` 直线切角占位 |
| 兼容旧 YAML | 未定 | 不在运行时兼容，未来单独 migrator |
| GDS scale | 预留 | 不实现 |
| GUI 元数据 | YAML 注释 | 不实现 |

原则：**MVP 文档优先级高于长期草案**。如果实现 MVP 时发现冲突，以本文件为准，之后再回填长期文档。

---

## 2. MVP 范围

### 2.1 必须包含

1. CLI 命令
   - `summer-gds validate <config.yaml>`
   - `summer-gds generate <config.yaml> --out <output.gds>`

2. YAML v1 解析器
   - 必须有 `schema_version: 1`
   - 必须严格校验字段、类型、数值范围和几何合法性
   - 必须输出结构化错误
   - 必须拒绝旧 YAML，而不是猜测兼容

3. 基础图形
   - `base_shape + polygon`
   - `base_shape + circle`

4. 倒角占位
   - 仅 `mode: bevel`
   - 仅 polygon 支持
   - circle 的 `fillet` 必须为 `null` 或省略

5. GDS 输出
   - 创建新 GDS
   - 创建指定 cell
   - 按 shape layer/datatype 写入 polygon
   - 输出文件可被 KLayout 打开

6. 测试
   - parser 单元测试
   - validator 单元测试
   - geometry 单元测试
   - CLI 集成测试
   - GDS 写出 smoke test

### 2.2 不在 MVP 范围

| 不做 | 原因 |
|---|---|
| GUI | 长期重要，但会拖入状态管理、下载、表单校验，影响核心内核收敛 |
| `rings` | 需要偏移链、环间距、布尔差和 fillet 半径序列，复杂度高 |
| `via` | 依赖内外偏移和布尔差，旧实现有 silent empty risk |
| `arc` fillet | fab 已反馈旧精度不对，新方案未定，不能在 MVP 中伪装可用 |
| `adaptive` fillet | 明确从长期规格中移除 |
| 旧 YAML 自动兼容 | 会污染新 parser，未来做单独 migrator |
| `gds.scale` | 容易和 dbu/precision/KLayout 单位耦合，先不做 |
| `layer_mapping` | GUI 可读性能力，MVP 只用数值 layer/datatype |
| GDS reverse reader | 与生成内核无关，后续工具化 |
| YAML 注释元数据 | PyYAML 不保留注释，MVP 不依赖注释 |

---

## 3. 架构原则

### 3.1 Boring by default

MVP 不引入复杂框架。使用 Python 标准库、PyYAML、KLayout 现有依赖、pytest。

### 3.2 严格协议，不做猜测

parser 只接受 canonical YAML v1。

禁止：

- 单值自动展开
- 字符串顶点兼容
- 旧字段名兼容
- 未知字段忽略
- shape 失败后继续生成其他 shape

任何错误都必须 fail fast，避免生成“看似成功但缺图形”的 GDS。

### 3.3 倒角接口先稳定，算法后升级

MVP 的 `bevel` 是接口占位，不是最终 fab 方案。未来 `arc_v2` 必须复用同一个 fillet strategy 接口，而不是侵入 parser、CLI 或 GDS writer。

`arc_v2` 的核心设计决策：

- YAML 继续面向用户，保持 `radii[i]` 对应 `vertices[i]` 的完整列表协议。
- 角对象只作为内部几何模型，不直接暴露到 YAML。
- 内部必须先构建 `CornerContext`，再由 fillet strategy 生成输出点。
- `CornerContext` 保存角的拓扑事实，例如用户序号、内部序号、前点、当前点、后点、凹凸性、半径。
- `ArcCornerPlan` 保存算法结果，例如切点、圆心、扫描方向、段数和输出点。
- 后续 GUI 可以支持“指定角”“所有凸角”“所有凹角”等编辑方式，但落盘必须展开为 canonical YAML。

这样做的目的不是增加抽象，而是把隐式规则显式化。倒角天然是逐角算法，如果继续在多个函数中手写 `points[i]`、`radii[i]`、方向翻转和凹凸判断，后续支持凹角、指定角、rings/via 时会形成不可读的隐式耦合。

### 3.4 模块边界优先于功能数量

MVP 功能少，但边界要完整：

- CLI 不懂几何细节
- YAML loader 不做业务默认值推导
- validator 不写 GDS
- geometry 不读 YAML
- GDS writer 不解析 shape schema

### 3.5 可回滚

旧系统不被删除、不被运行时混入。MVP 使用新的入口和新协议。后续如果 MVP 方向不对，可以独立回滚，不影响旧流程。

---

## 4. 建议目录结构

这是实施建议，不要求一次性完全照搬文件名，但边界必须保留。

```text
mvp/
  README.md
  src/
    mvp_summer_gds/
      cli.py                 # CLI 参数解析，调用 application service
      app.py                 # validate/generate 用例编排
      config/
        loader.py            # 读取 YAML，禁止业务推导
        schema.py            # 字段白名单、类型校验、版本分发
        errors.py            # 结构化错误模型
      model.py               # NormalizedConfig / Shape / Layer 等领域模型
      geometry/
        primitives.py        # Point / Polygon 数据结构与基础校验
        corners.py           # CornerContext / CornerKind / ArcCornerPlan
        circle.py            # circle 离散化
        fillet.py            # fillet strategy，占位 bevel
      gds/
        writer.py            # 将 normalized geometry 写成 GDS
  tests/
    fixtures/
      valid_polygon.yaml
      valid_polygon_bevel.yaml
      valid_circle.yaml
    unit/
      test_yaml_schema.py
      test_geometry_base_shape.py
      test_bevel_fillet.py
      test_cli.py
      test_gds_writer.py
    visual/
      test_png_snapshots.py
    _visual_output/          # pytest 生成的人工审查 PNG
```

目录原则：

- `mvp/` 是第一阶段唯一可运行的新实现边界，旧系统代码不得 import MVP 内部模块。
- `mvp_summer_gds` 是内部包名，避免和旧系统或未来重构后的正式包名冲突。
- 对外 CLI 仍保持 `summer-gds`，降低用户命令层面的迁移成本。
- 后续 `rings`、`via`、`arc_v2`、GUI 适配应先在 `mvp/` 内完成协议和测试迭代，再决定是否提升为正式核心。

复杂度预算：

- MVP 目标实现文件：6 到 8 个核心文件
- 新抽象数量：最多 2 个稳定接口
- 稳定接口建议：
  - `ShapeRenderer`
  - `FilletStrategy`
- 允许新增一个轻量数据模型族：
  - `CornerContext`
  - `ArcCornerPlan`

`CornerContext` 不是 service，不算新业务边界；它是几何算法的显式输入数据结构。

如果实现开始触碰超过 10 个核心文件，说明设计开始膨胀，需要停下来拆回 MVP。

---

## 5. 数据流

```text
             CLI args
                |
                v
        +----------------+
        |   cli.py       |
        +----------------+
                |
                v
        +----------------+
        |   app.py       |
        +----------------+
          |            |
          | validate   | generate
          v            v
  +----------------+  +----------------+
  | YAML loader    |  | YAML loader    |
  +----------------+  +----------------+
          |            |
          v            v
  +----------------+  +----------------+
  | schema validator| | schema validator|
  +----------------+  +----------------+
          |            |
          v            v
  +----------------+  +----------------+
  | normalized model| | normalized model|
  +----------------+  +----------------+
                       |
                       v
                +-------------+
                | geometry    |
                +-------------+
                       |
                       v
                +-------------+
                | GDS writer  |
                +-------------+
                       |
                       v
                   output.gds
```

错误路径：

```text
YAML parse error
  -> ConfigError(path="$", code="yaml_parse_error")

Schema/type error
  -> ConfigError(path="shapes[0].vertices[2][1]", code="invalid_type")

Geometry error
  -> ConfigError(path="shapes[0]", code="self_intersecting_polygon")

GDS writer error
  -> RuntimeError(code="gds_write_failed")
```

所有错误必须带：

- `path`：字段路径
- `code`：稳定错误码
- `message`：面向开发者的清晰说明
- `hint`：面向用户的修复建议

---

## 6. YAML v1 协议

### 6.1 顶层结构

```yaml
schema_version: 1

global:
  dbu: 0.001
  precision: null

gds:
  output_file: "output.gds"
  cell_name: "TOP"
  default_layer: [1, 0]

shapes:
  - id: "main_pad"
    type: "base_shape"
    geometry_type: "polygon"
    layer: [1, 0]
    vertices:
      - [0, 0]
      - [100, 0]
      - [100, 80]
      - [0, 80]
    fillet: null
```

### 6.2 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | `int` | 是 | MVP 固定为 `1` |
| `global` | `object` | 是 | 全局数值规则 |
| `gds` | `object` | 是 | 输出配置 |
| `shapes` | `list[object]` | 是 | 图形列表，至少 1 个 |

未知顶层字段：必须报错。

### 6.3 `global`

| 字段 | 类型 | 必填 | 默认值 | 规则 |
|---|---|---|---|---|
| `dbu` | `float` | 否 | `0.001` | `0.00001 <= dbu <= 1.0` |
| `precision` | `float | null` | 否 | `null` | `null` 或 `0.00001 <= precision <= 1.0` |

如果 `precision` 不为 `null`，必须满足：

```text
precision / dbu 是整数
```

原因：避免坐标四舍五入后落不到 GDS 数据库单位网格上。

### 6.4 `gds`

| 字段 | 类型 | 必填 | 默认值 | 规则 |
|---|---|---|---|---|
| `output_file` | `string` | 是 | 无 | 文件名必须以 `.gds` 结尾 |
| `cell_name` | `string` | 是 | 无 | 非空，只允许 `[A-Za-z0-9_.$-]` |
| `default_layer` | `[int, int]` | 否 | `[1, 0]` | `[layer, datatype]` |

不支持：

- `default_layer: 1` 加 `default_datatype: 0`
- `scale`
- `input_file`
- `layer_mapping`

### 6.5 shape 通用字段

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | `string` | 是 | 全局唯一，稳定引用 ID |
| `type` | `string` | 是 | MVP 只允许 `base_shape` |
| `geometry_type` | `string` | 是 | `polygon` 或 `circle` |
| `name` | `string` | 否 | 展示名，不参与逻辑 |
| `layer` | `[int, int]` | 否 | 省略则使用 `gds.default_layer` |
| `fillet` | `object | null` | 否 | 默认 `null` |

未知字段：必须报错。

---

## 7. 图形定义

### 7.1 `base_shape + polygon`

```yaml
- id: "main_pad"
  type: "base_shape"
  geometry_type: "polygon"
  layer: [1, 0]
  vertices:
    - [0, 0]
    - [100, 0]
    - [100, 80]
    - [0, 80]
  fillet:
    mode: "bevel"
    distances: [5, 5, 5, 5]
```

规则：

- `vertices` 至少 3 个点
- 每个点必须是 `[x, y]`
- `x/y` 必须是有限数值，禁止 `NaN` / `inf`
- 不允许连续重复点
- 不允许首尾重复点
- 不允许零面积 polygon
- MVP 建议只接受简单 polygon
- 如果启用 `bevel`，MVP 只接受凸 polygon

顶点方向：

- parser 可以接受顺时针或逆时针
- normalized model 内部统一为逆时针
- 错误消息和 fillet `distances` 仍按用户输入顺序定位

原因：旧核心偏移逻辑以逆时针为前提，MVP 先继承这个内部约定，避免方向语义反复切换。

### 7.2 `base_shape + circle`

```yaml
- id: "round_pad"
  type: "base_shape"
  geometry_type: "circle"
  layer: [1, 0]
  center: [50, 50]
  radius: 30
  fillet: null
```

规则：

- `center` 必须是 `[x, y]`
- `radius > 0`
- `fillet` 必须为 `null` 或省略
- circle 内部离散化为 polygon 后写入 GDS
- MVP 固定使用 `128` 段离散化，不暴露配置项

未来如果需要控制圆精度，新增字段应命名为 `segments` 或 `chord_error`，但不进入 MVP。

---

## 8. 倒角占位接口

### 8.1 支持的唯一模式：`bevel`

```yaml
fillet:
  mode: "bevel"
  distances: [5, 5, 5, 5]
```

语义：

- `distance = 0`：该角不处理
- `distance > 0`：沿入边和出边分别截断指定距离，用直线连接两个截断点
- `distances.length == vertices.length`

示意：

```text
原始角:

       Pnext
        /
       /
      P
      |
      |
    Pprev

bevel 后:

       Pnext
        /
       A
      /
     B
     |
     |
   Pprev
```

### 8.2 明确不支持

以下输入必须报错：

```yaml
fillet:
  mode: "arc"
```

```yaml
fillet:
  mode: "adaptive"
```

```yaml
fillet:
  radii: [5, 5, 5, 5]
```

原因：旧圆弧倒角存在 fab 精度问题，MVP 不应暴露会被误解为生产可用的接口。

### 8.3 bevel 校验

对每个顶点 `i`：

- `distance[i] >= 0`
- `distance[i]` 必须是有限数值
- `distance[i]` 不能超过相邻边长度的安全上限
- 如果相邻两个角在同一边上的 cut distance 之和大于等于边长，必须报错

建议安全规则：

```text
distance_at_edge_start + distance_at_edge_end < edge_length
```

不要自动缩小距离。自动修正会让用户以为参数生效，但实际输出不同。

### 8.4 下一阶段：`arc_v2`

下一阶段在 MVP 内加入圆弧倒角，但不替换 `bevel`。`bevel` 保留为占位实现和回归对照。

```yaml
fillet:
  mode: "arc_v2"
  radii: [5, 0, 10, 3]
```

协议语义：

- `mode` 必须显式为 `arc_v2`
- `radii.length == vertices.length`
- 第 `i` 个半径严格对应用户输入的第 `i` 个顶点
- `radius = 0` 表示该角不倒角
- `radius < 0` 必须报错
- circle 继续禁止 fillet
- 旧 `mode: "arc"` 继续报错
- 裸 `fillet.radii` 继续报错，避免和旧协议混淆

内部数据流：

```text
PolygonShape.vertices + ArcFillet.radii
        |
        v
build_corner_contexts()
        |
        v
CornerContext[]
  ├── user_index          # 用户输入顶点序号
  ├── normalized_index    # CCW normalize 后的内部序号
  ├── prev_point
  ├── vertex
  ├── next_point
  ├── incoming_edge
  ├── outgoing_edge
  ├── turn_sign
  ├── corner_kind         # convex / concave / collinear
  └── radius
        |
        v
ArcCornerPlan[]
  ├── tangent_start
  ├── tangent_end
  ├── center
  ├── sweep_direction
  ├── segment_count
  └── output_points
```

规划边界：

- 第一版 `arc_v2` 只支持 simple + convex polygon。
- 如果存在 concave corner，报 `arc_v2_requires_convex_polygon`，不尝试自动处理。
- 如果相邻两个角在同一边上的 tangent distance 之和大于等于边长，报 `arc_radius_too_large`。
- 不自动缩小半径。
- 不暴露 YAML `tolerance`，段数由内部策略根据半径和精度计算。
- 不复用旧 `gds_utils.Frame._apply_arc_fillet_internal()`。

后续能力通过 `CornerContext` 实现，不改变 canonical YAML：

```text
GUI / authoring layer
  ├── 指定 user_index = 2 的角
  ├── 选择所有 convex 角
  └── 选择所有 concave 角
          |
          v
展开为完整 radii 列表
          |
          v
canonical YAML v1
```

---

## 9. Validator 规则

### 9.1 通用 YAML 规则

- 必须是 YAML mapping
- 必须有 `schema_version: 1`
- 必须有 `global`、`gds`、`shapes`
- `shapes` 必须非空
- 所有未知字段报错
- 所有数值必须有限
- 所有列表长度必须精确匹配

### 9.2 旧 YAML 拒绝策略

如果检测到旧字段，返回专门错误：

| 旧字段 | 错误码 | hint |
|---|---|---|
| `type: polygon` | `old_schema_detected` | 使用 `type: base_shape` + `geometry_type: polygon` |
| `ring_num` | `unsupported_mvp_shape` | `rings` 不在 MVP 范围 |
| `ring_width` | `unsupported_mvp_shape` | `rings` 不在 MVP 范围 |
| `fillet.type` | `old_fillet_schema` | MVP 只支持 `fillet.mode: bevel` |
| `vertices_gen` | `unsupported_generator` | 生成器不在 MVP 范围 |

不要尝试兼容转换。未来单独做：

```bash
summer-gds migrate old.yaml --to-schema 1 --out new.yaml
```

### 9.3 几何规则

polygon 必须满足：

- 点数 >= 3
- 无连续重复点
- 首尾不重复
- 面积非零
- 不自交
- bevel 模式下为凸多边形

circle 必须满足：

- `radius > 0`
- `center` 合法
- `fillet` 为 `null`

---

## 10. CLI 规格

### 10.1 `validate`

```bash
summer-gds validate config.yaml
```

行为：

- 只读取和校验 YAML
- 不写 GDS
- 成功输出简短摘要
- 失败输出结构化错误列表

成功示例：

```text
OK: config.yaml
schema_version: 1
shapes: 2
output_file: output.gds
```

失败示例：

```text
ERROR config_invalid
- path: shapes[0].fillet.mode
  code: unsupported_fillet_mode
  message: MVP only supports fillet.mode = "bevel".
  hint: Use fillet: null or fillet.mode: bevel.
```

### 10.2 `generate`

```bash
summer-gds generate config.yaml --out output.gds
```

行为：

1. 先执行完整 validate
2. validate 失败则不创建 GDS
3. validate 成功后生成几何
4. 写入 GDS
5. 输出摘要

成功示例：

```text
OK: output.gds
cell: TOP
shapes_written: 2
polygons_written: 2
```

### 10.3 退出码

| 退出码 | 含义 |
|---:|---|
| `0` | 成功 |
| `1` | 文件 IO 错误 |
| `2` | YAML/schema/geometry 校验失败 |
| `3` | GDS 写出失败 |
| `4` | CLI 参数错误 |

---

## 11. GDS Writer 规则

输入必须是 normalized geometry，不接受 YAML dict。

建议内部对象：

```text
RenderedPolygon
  id: string
  layer: tuple[int, int]
  points: list[Point]
```

writer 只负责：

- 创建 layout
- 设置 dbu
- 创建 cell
- 创建 layer
- 插入 polygon
- 写文件

writer 不负责：

- YAML 字段默认值
- fillet 算法
- circle 离散化
- shape 类型分发
- old schema 兼容

---

## 12. 扩展点

### 12.1 新 shape：`rings`

未来加入 `rings` 时，只应新增：

- YAML schema 分支
- `RingsRenderer`
- geometry ring builder
- 对应测试

不应修改：

- CLI 命令语义
- error model
- GDS writer 输入格式

### 12.2 新 shape：`via`

未来加入 `via` 时，必须先解决：

- `outer_zoom > inner_zoom` 强校验
- 布尔差为空的错误处理
- 内外边界方向和 fillet 顺序
- 旧实现 silent empty 的回归测试

### 12.3 新 fillet：`arc_v2`

未来圆弧倒角必须作为新 mode：

```yaml
fillet:
  mode: "arc_v2"
  radii: [5, 5, 5, 5]
```

设计约束：

- `arc_v2` 复用第 8.4 节的 `CornerContext` 管线。
- YAML 不暴露角对象，只暴露完整 `radii` 列表。
- `radii[i]` 永远对应用户输入的第 `i` 个顶点。
- 顶点被 normalize 为 CCW 时，内部必须同步维护 `user_index` 映射，不能让半径错位。
- 第一版只支持 convex polygon；concave polygon 必须显式报错。
- 段数和精度策略内部计算，不在 YAML 暴露 `tolerance`。

进入条件：

- 有 `CornerContext` 单元测试
- 有最小制造验收样例
- 有几何误差测试
- 有不同 dbu/precision 下的输出一致性测试
- 有 PNG visual snapshot，方便人工审查

禁止复用旧 `mode: arc` 名称，避免和旧语义混淆。

### 12.4 GUI

GUI 后续只应生成 canonical YAML v1，不应绕过 parser。

```text
GUI form state
  -> canonical YAML v1
  -> same parser
  -> same validator
  -> same generator
```

这样 GUI 和 CLI 使用同一条后端路径，避免两套规则漂移。

### 12.5 旧 YAML migrator

兼容必须作为离线转换工具，而不是 generator 运行时分支：

```text
old YAML
  -> migrator
  -> canonical YAML v1
  -> parser
  -> generator
```

原因：

- 兼容逻辑可测试、可删除
- 生成路径保持简单
- 用户能看到迁移结果，而不是隐藏转换

---

## 13. 测试方案

### 13.1 覆盖图

```text
CODE PATHS                                      TEST REQUIREMENTS

CLI validate
  ├── valid yaml                                unit/integration: exit 0
  ├── missing file                              integration: exit 1
  ├── malformed yaml                            integration: exit 2
  ├── old schema                                integration: exit 2 + old_schema_detected
  └── unknown field                             integration: exit 2 + field path

YAML parser
  ├── schema_version = 1                        unit: accepted
  ├── schema_version missing                    unit: rejected
  ├── schema_version unsupported                unit: rejected
  ├── NaN / inf                                 unit: rejected
  └── default layer applied                     unit: normalized model

base_shape polygon
  ├── valid square                              unit: accepted
  ├── clockwise input                           unit: normalized to CCW
  ├── repeated point                            unit: rejected
  ├── zero area                                 unit: rejected
  ├── self intersection                         unit: rejected
  └── invalid layer                             unit: rejected

base_shape circle
  ├── valid circle                              unit: 128-point polygon
  ├── radius = 0                                unit: rejected
  ├── radius < 0                                unit: rejected
  └── fillet not null                           unit: rejected

bevel fillet
  ├── null fillet                               unit: unchanged polygon
  ├── valid distances                           unit: deterministic vertices
  ├── length mismatch                           unit: rejected
  ├── negative distance                         unit: rejected
  ├── too large for edge                        unit: rejected
  └── concave polygon                           unit: rejected

corner context
  ├── user_index preserved                      unit: input order remains traceable
  ├── normalized_index assigned                 unit: internal CCW order is explicit
  ├── clockwise input                           unit: radius mapping follows user_index
  ├── convex corner classified                  unit: corner_kind = convex
  ├── concave corner classified                 unit: corner_kind = concave
  └── collinear corner classified               unit: corner_kind = collinear

arc_v2 fillet
  ├── valid radii                               unit: deterministic arc points
  ├── mixed per-corner radii                    unit: each radius affects its own corner
  ├── zero radius                               unit: original corner preserved
  ├── length mismatch                           unit: rejected
  ├── negative radius                           unit: rejected
  ├── too large for edge                        unit: rejected
  ├── clockwise input                           unit: user_index/radius mapping preserved
  ├── concave polygon                           unit: rejected in first arc_v2 phase
  └── bare fillet.radii                         unit: rejected as old/ambiguous schema

GDS writer
  ├── writes output file                        integration
  ├── correct cell name                         integration via KLayout load
  ├── correct layer/datatype                    integration via KLayout load
  └── no silent empty output                    integration: rejected earlier

Visual snapshots
  ├── valid polygon renders PNG                 integration via parser + renderer
  ├── bevel polygon renders PNG                 integration via parser + renderer
  ├── circle approximation renders PNG          integration via parser + renderer
  ├── arc_v2 polygon renders PNG                integration via parser + renderer
  └── output is non-empty                        smoke: file exists and has bytes
```

### 13.2 Required fixtures

```text
mvp/tests/fixtures/
  valid_polygon.yaml
  valid_polygon_bevel.yaml
  valid_polygon_arc_v2.yaml
  valid_polygon_arc_v2_mixed.yaml
  valid_circle.yaml
  invalid_old_polygon.yaml
  invalid_arc_fillet.yaml
  invalid_arc_v2_concave.yaml
  invalid_arc_v2_too_large.yaml
  invalid_self_intersection.yaml
  invalid_bevel_too_large.yaml
```

### 13.3 Regression tests from old system

必须锁住这些旧系统问题：

| 风险 | MVP 测试 |
|---|---|
| shape 解析失败后被跳过，仍生成 GDS | 任一 shape 无效时整个 generate 失败 |
| 新 fillet schema 被旧代码静默忽略 | `fillet.radii` without `mode` 必须报错 |
| 顶点方向和 radii 顺序错位 | clockwise 输入 + `CornerContext.user_index` 必须保持用户角位映射 |
| via 布尔差为空但继续输出 | via 不在 MVP，输入必须直接失败 |
| 旧字符串 vertices 分隔符混乱 | 字符串 vertices 必须报错 |

---

## 14. 性能约束

MVP 不追求大规模版图生成，但必须设置硬上限，避免 CLI 卡死。

建议默认限制：

| 项 | 上限 |
|---|---:|
| shapes 数量 | `100` |
| polygon 顶点数 | `10_000` |
| circle 离散段数 | `128` |
| bevel 后单 shape 顶点数 | `20_000` |
| 总输出 polygon 顶点数 | `100_000` |

如果超过限制，validator 报错，不进入 GDS writer。

后续如需放宽，应先增加基准测试：

```text
100 shapes x 1_000 vertices
1 shape x 10_000 vertices + bevel
mixed polygon/circle 100 shapes
```

---

## 15. 实施阶段

### Phase 0：文档冻结

输出：

- 本文档
- README 索引更新
- MVP YAML 示例冻结

完成标准：

- MVP 范围明确
- 不在范围内的能力明确
- 后续扩展点明确

### Phase 1：Parser + Validator

输出：

- YAML loader
- schema validator
- normalized model
- structured errors
- parser/validator tests

完成标准：

- 所有 invalid fixture 都失败
- 所有 valid fixture 都生成 normalized model
- 旧 YAML 明确报 `old_schema_detected`

### Phase 2：Geometry

输出：

- polygon 校验
- circle 离散化
- bevel strategy
- geometry tests

完成标准：

- polygon/circle/bevel 输出确定性点集
- 非法几何不进入 writer

### Phase 3：GDS Writer + CLI

输出：

- `validate`
- `generate`
- GDS writer
- CLI tests
- GDS smoke tests

完成标准：

- valid fixtures 生成可打开 GDS
- invalid fixtures 不创建 GDS
- 退出码符合规范

### Phase 4：MVP hardening

输出：

- 性能 guardrail
- 错误消息 polish
- 快速手工验证指南

完成标准：

- 错误可定位到字段路径
- KLayout 手工打开通过
- 没有 silent skip

### Phase 5：`arc_v2` 圆弧倒角迭代

输出：

- `CornerContext` / `CornerKind` / `ArcCornerPlan` 内部模型
- `arc_v2` YAML parser 和 validator
- convex-only `arc_v2` 几何实现
- `arc_v2` fixtures
- `arc_v2` geometry、CLI、GDS、PNG visual tests

完成标准：

- `radii[i]` 与用户输入顶点 `vertices[i]` 的角位绑定可测试
- clockwise 输入 normalize 后不丢失 `user_index` 映射
- mixed per-corner radii 输出确定性点集
- concave polygon 明确报 `arc_v2_requires_convex_polygon`
- 过大半径明确报 `arc_radius_too_large`
- 裸 `fillet.radii` 继续被拒绝，避免旧协议回流
- `valid_polygon_arc_v2.yaml` 可生成 GDS 和 PNG 快照

---

## 16. 验收标准

MVP 完成必须同时满足：

1. `summer-gds validate mvp/tests/fixtures/valid_polygon.yaml` 成功
2. `summer-gds generate mvp/tests/fixtures/valid_polygon.yaml --out /tmp/polygon.gds` 成功
3. `valid_circle.yaml` 生成的 GDS 可被 KLayout 读取
4. `valid_polygon_bevel.yaml` 输出确定性 GDS
5. `invalid_old_polygon.yaml` 明确失败，错误码为 `old_schema_detected`
6. `invalid_arc_fillet.yaml` 明确失败，错误码为 `unsupported_fillet_mode`
7. 任意 shape 无效时不生成部分 GDS
8. 测试覆盖 parser、validator、geometry、CLI、GDS writer
9. `uv run python -m pytest mvp/tests/visual` 生成可人工审查的 PNG 快照

---

## 17. 关键决策记录

| 决策 | 选择 | 原因 |
|---|---|---|
| MVP 主入口 | CLI-first | 降低重构面，先验证核心生成链路 |
| 旧 YAML | 不运行时兼容 | 避免兼容泥潭，未来 migrator 单独做 |
| 顶点格式 | 数值对列表 | 强类型、易校验、少分隔符边界 |
| 倒角 | `bevel` 占位 | 不复用 fab 已反馈有问题的旧 arc |
| 下一阶段倒角 | `mode: arc_v2` + `radii` | 显式区分新旧圆弧语义 |
| 角对象 | 内部 `CornerContext`，不进入 YAML | 保持用户协议简单，同时让算法显式可读 |
| `arc_v2` 范围 | 第一版只支持 convex polygon | concave 语义复杂，先识别并明确报错 |
| `arc_v2` 精度 | 内部策略，不暴露 YAML `tolerance` | 减少用户配置面，避免精度参数和 dbu/precision 混乱 |
| circle 精度 | 固定 128 段 | MVP 保持确定性，不提前暴露调参 |
| shape 范围 | 仅 `base_shape` | rings/via 都依赖更复杂几何和布尔差 |
| 错误策略 | fail fast | 禁止 silent skip 和部分成功 |

---

## 18. Open Questions

这些问题不阻塞 MVP，但需要在后续迭代前确认：

1. `arc_v2` 内部精度策略的 fab 验收口径是什么：弦高误差、半径误差、还是 GDS 网格误差？
2. circle 后续是否需要用户控制 `segments` 或 `chord_error`？
3. old YAML migrator 是否需要保证 GDS 等价，还是只保证字段语义迁移？
4. `rings` 的 `ring_spaces` 是否应为 `ring_count` 项还是 `ring_count - 1` 项？
5. GUI 是否必须保存用户简化输入，还是只保存 canonical YAML？

---

## 19. 推荐下一步

下一步不要直接写 arc 算法。先把角对象和协议边界钉住。

建议顺序：

1. 新增 `CornerContext` / `CornerKind` / `ArcCornerPlan` 设计与测试
2. 用 `CornerContext` 覆盖 clockwise normalize、user_index、convex/concave/collinear 分类
3. 新增 `arc_v2` fixtures：valid、mixed radii、concave invalid、too-large invalid
4. 实现 parser/validator 到所有 `arc_v2` fixture 通过
5. 实现 convex-only arc geometry
6. 加 GDS smoke test 和 PNG visual snapshot

这样可以先验证“每个角是显式对象”的设计，避免圆弧算法把隐式状态重新塞回 `points[i]` 和 `radii[i]`。
