# 前端交互与页面设计 v2.6

文档版本：v2.6
日期：2026-05-25
状态：方案设计

---

## 1. 设计目标

- 用户通过可视化配置构建器编辑 YAML v2 配置，无需手写 YAML。
- 支持 `base_shape`、`via`、`rings` 三类公开 shape。
- YAML 是唯一持久化真源；表单会生成 YAML，实时 SVG 预览、保存和导出都使用这份 YAML。
- GUI 产品产物只有 YAML 和 GDS。
- SVG 仅用于实时预览，不提供下载或导出入口。
- 所有导出/保存都通过 PC 原生文件对话框完成。

## 2. 非目标

第一版 GUI 不做：

- PNG 导出。
- SVG 导出。
- 批量创建多个 `rings` shape。
- 老版 `ring_width` / `ring_space` 字符串规则。
- 老版 linkage、继承、override 系统。
- 复杂移动端响应式布局。

## 3. 桌面布局

第一版面向 PC 桌面窗口，采用稳定双栏布局，避免复杂响应规则。视觉 tokens、DOM class 和组件 CSS 由 [前端设计系统](./frontend-design-system.md) 定义。

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Summer GDS v2      YAML: modified      Preview: ready      GDS: not saved  │
│ [打开 YAML] [保存 YAML] [校验] [导出 GDS]                      status text  │
├──────────────────────────────────────────┬─────────────────────────────────┤
│ [构建器] [YAML 预览]        [全局设置]     │ 实时 SVG 预览区                    │
│                                          │                                 │
│ [+ Base Shape] [+ Via] [+ Rings]         │ ┌─ SVG Preview ───────────────┐ │
│                                          │ │ [Fit] [Zoom +] [Zoom -]     │ │
│  shape card list                         │ │                             │ │
│  #0 base_shape                           │ │        centered live SVG    │ │
│  #1 via                                  │ │                             │ │
│  #2 rings                                │ │                             │ │
│                                          │ │                             │ │
│                                          │ └─────────────────────────────┘ │
└──────────────────────────────────────────┴─────────────────────────────────┘
```

布局规则：

- 最佳设计目标：标准 16:9 的 `1280x720`。
- 最小支持分辨率：`640x360`。低于最佳尺寸时允许横向/纵向滚动，不做移动端重排。
- 操作区和预览区初始比例为 `1:1`。
- 用户可以拖拽中间 splitter 调整比例，第一版限制在 `35:65` 到 `65:35`。
- 左侧默认是 `构建器` 模式，主要空间用于 shape 列表。
- `YAML 预览` 是只读模式切换，不是底部常驻面板。
- 不使用 `Global / Shapes / Generated YAML` 三个传统 tab；Global 设置通过按钮打开弹层或抽屉。
- shape 列表内部滚动，添加后的所有 shape 都必须在左侧可见；放不下时滚动。
- 坐标列表和 YAML 预览内部滚动，不挤压整页。
- 模态框最大高度 `80vh`，内容区滚动。
- 第一版取消独立日志区。状态、错误和成功提示显示在顶部 status text、字段旁错误和预览错误态中。

## 4. 顶部操作

| 操作 | 行为 |
| --- | --- |
| `打开 YAML` | 打开原生文件对话框，读取 `.yaml`/`.yml`，parse 成功后回填表单。dirty 时先确认是否丢弃未保存修改。 |
| `保存 YAML` | 打开原生保存对话框选择路径，必要时确认覆盖，然后保存当前 YAML。 |
| `校验` | 调 `/api/validate`，显示字段错误和顶部状态。 |
| `导出 GDS` | 打开原生保存对话框选择 `.gds` 路径，必要时确认覆盖，然后导出。 |

不提供：

- `Export PNG`
- `Export SVG`
- `Download preview`

## 5. 左侧工作区

左侧工作区只承担一个职责：让用户通过可见对象构建 YAML。用户不需要理解内部有 `global`、`shapes`、`generated yaml` 三个技术区块。

### 5.1 模式切换栏

顶部使用按钮式模式切换，不使用 tab 组件。

```text
[构建器] [YAML 预览]                         [全局设置]
```

规则：

- `构建器` 是默认模式。
- `YAML 预览` 显示当前生成 YAML 的只读全文。
- `全局设置` 是独立按钮，打开弹层或侧边抽屉；关闭后不占用左侧主区域。
- 如果 global 设置已完成，左侧主区域不持续展示 global 表单，只在顶部或状态 pill 显示摘要，例如 `dbu 0.001 / TOP`。
- 模式切换不改变数据源；构建器和 YAML 预览都读取同一份 `formDraft -> generatedYamlText`。

### 5.2 Global 设置弹层

Global 设置编辑配置中的 `global` 和 GDS 必要配置，但不是左侧常驻面板。

```text
┌─ 全局设置 ────────────────────────────┐
│ dbu:       [ 0.001    ]  (0.00001~1)  │
│ precision: [          ]  optional     │
│ unit:       um (fixed)                │
│                                       │
│ top_cell:  [ TOP         ]            │
│ output:    由导出 GDS 管理             │
│                                       │
│ [取消] [应用]                         │
└───────────────────────────────────────┘
```

说明：

- `unit` 第一版固定为 `um`。
- `top_cell` 是 GDS 导出必需字段。
- GUI 导出路径不依赖 `gds.output` 输入框；用户点击 `导出 GDS` 时选择保存位置。
- 新建配置默认不生成 `gds.output`。
- 如果加载的 YAML 已有 `gds.output`，form draft 记录该字段，YAML 预览保留显示，并在 Global 设置中只读展示为 `CLI 默认输出`。
- GUI 不提供编辑 `gds.output` 的输入框，也不会把 `导出 GDS` 选择的路径写回 `gds.output`。
- 保存 YAML 时，如果原文件带 `gds.output`，规范化 YAML 应保留该字段；如果原文件没有，GUI 不主动新增。
- GUI 导出 GDS 始终使用本次保存对话框路径，通过后端导出选项覆盖 YAML 中的 `gds.output`。

### 5.3 构建器模式

构建器模式是左侧默认页面。顶部提供快速添加入口：

```text
[+ Base Shape] [+ Via] [+ Rings]
```

交互规则：

- `+ Base Shape` 打开 base_shape 创建弹层。
- `+ Via` 打开 source 选择弹层；如果没有 base_shape，则按钮禁用或显示“先创建 base_shape”。
- `+ Rings` 打开 source 选择弹层；如果没有 base_shape，则按钮禁用或显示“先创建 base_shape”。
- 更推荐的创建路径是在某个 base_shape 卡片上点击 `Create Via` 或 `Create Rings`，这样 source 已明确。
- 创建成功后，新 shape 立即出现在左侧 shape 列表中。
- 左侧列表按 YAML `shapes` 顺序展示；第一版不提供拖拽排序。
- 编辑 shape 打开弹层/抽屉，不在列表里展开巨大表单，避免占用 shape 列表空间。
- 删除 shape 必须二次确认。
- 如果删除的 base_shape 被 via/rings/source ref 引用，第一版默认阻止删除，并提示先删除依赖 shape；不做自动级联删除。

### 5.4 Shape 列表

shape 列表是构建器模式的主体。

```text
┌ #0 source_pad             base_shape ─────────────┐
│ layer [1,0] | vertices 4 | fillet none            │
│ actions: Edit Delete Offset Copy Create Via Rings │
└───────────────────────────────────────────────────┘
┌ #1 contact                via ← #0 ───────────────┐
│ layer [10,0] | inner -5 | outer +8                │
│ fillet inner none | outer r=2                     │
│ actions: Edit Delete                              │
└───────────────────────────────────────────────────┘
┌ #2 guard                  rings ← #0 ─────────────┐
│ layer [20,0] | count 3 | pitch 12 | width 4       │
│ actions: Edit Delete                              │
└───────────────────────────────────────────────────┘
```

卡片摘要必须显示：

- `sid`
- `name`
- `type`
- `layer`
- source 信息：direct vertices 或 `ref #sid`
- 关键参数：顶点数量、offset、via inner/outer、rings count/pitch/width
- 倒角摘要：none、shared radius、inner/outer radius、per-ring radius
- 错误状态：字段错误或后端 validate 错误必须能定位到对应卡片

#### base_shape 卡片

```text
┌ #0 base_shape "source_pad" ─────────────────────────────┐
│ Layer [1,0] | vertices: 4 | fillet: arc r=2              │
│ [Edit] [Delete] [Offset Copy] [Create Via] [Create Rings]│
└──────────────────────────────────────────────────────────┘
```

展开编辑：

```text
sid:      0
name:     [ source_pad ]
layer:    [ 1 ] / [ 0 ]

source:
  (●) vertices
  ( ) ref + offset

vertices:
  坐标列表                [格式化]
  4 点 · 逆时针 · 面积 8000
  ┌────┬──────────────────────────┐
  │ 1  │ 0,0                      │
  │ 2  │ 100,0                    │
  │ 3  │ 100,80                   │
  │ 4  │ 0,80                     │
  └────┴──────────────────────────┘

fillet:
  (●) none
  ( ) unified radius [ 2 ] um
  ( ) per-corner radii

per-corner radii:
  半径列表                [格式化]
  4 个半径 · 匹配 4 个顶点
  ┌──────────────────────────────────────────┐
  │ 1, 2, 0, 3                              │
  └──────────────────────────────────────────┘
```

#### offset copy

`Offset Copy` 创建新的 `base_shape`：

```yaml
source:
  ref: <current sid>
  offset: <user input>
```

该新 shape 是公开输出对象，不是 internal/helper shape。

#### via 卡片

```text
┌ #1 via "contact" ← #0 ───────────────────────────────┐
│ Layer [10,0] | inner:-5 | outer:+8                   │
│ Fillet: inner r=1 | outer r=2                         │
│ [Edit] [Delete]                                      │
└──────────────────────────────────────────────────────┘
```

via 支持 inner/outer 独立倒角。

#### rings 卡片

```text
┌ #2 rings "guard" ← #0 ───────────────────────────────┐
│ Layer [20,0] | count:3 | pitch:12 | width:4           │
│ Fillet: per-ring inner/outer                          │
│ [Edit] [Delete]                                      │
└──────────────────────────────────────────────────────┘
```

第一版的 `rings` 是**单个 rings shape**：一个 YAML shape 通过 `count/pitch/width` 生成多圈 ring region。

不提供“批量 rings”功能，也就是不提供一次生成多个独立 `type: rings` shape 的交互。

### 5.5 YAML 预览模式

YAML 预览模式展示由配置构建器生成的完整 YAML。第一版默认只读，不作为普通用户输入入口。

```yaml
schema_version: 2
global:
  unit: um
  dbu: 0.001
gds:
  top_cell: TOP
shapes:
  - type: base_shape
    sid: 0
    name: source_pad
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
```

同步规则：

- 表单编辑会生成规范 YAML。
- 生成的 YAML 每次 parse 成功后会规范化显示。
- 打开 YAML 文件时，parse 成功才同步回表单。
- 打开 YAML 文件 parse 失败时，不覆盖当前表单，显示导入错误。
- `yaml_invalid` 状态通常来自表单生成结果不满足协议；该状态下禁用预览和 GDS 导出。
- 第一版不提供主界面手写 YAML 编辑。后续若增加高级 Raw YAML 模式，必须单独设计确认和恢复流程。
- YAML 预览不在左侧底部常驻；只有切换到 `YAML 预览` 模式时显示。

### 5.6 表单和 YAML 映射规则

#### schema_version

- `schema_version: 2` 由前端序列化器自动写入。
- 第一版不在 UI 中暴露 schema version 输入框。
- 打开 YAML 时，如果 `schema_version` 缺失或不是 `2`，显示明确导入错误，不自动迁移旧协议。

#### 坐标列表输入

坐标列表输入是 `source.vertices` 的 UI 表达。第一版不提供顶点表格；大量坐标应通过列表粘贴、脚本生成和格式化完成。

```text
坐标列表                [格式化]
4 点 · 逆时针 · 面积 8000

1  0,0
2  100,0
3  100,80
4  0,80
```

序列化为：

```yaml
source:
  vertices:
    - [0, 0]
    - [100, 0]
    - [100, 80]
    - [0, 80]
```

规则：

- 行顺序就是多边形顶点顺序。
- 前端不自动插入闭合点；用户不需要重复第一点作为最后一点。
- 每行必须能解析为两个有限数值，分别序列化为 `[x, y]`。
- 支持每行一个点、分号分隔、旧版冒号分隔和 JSON/YAML 数组子集。
- `格式化` 将当前合法坐标统一写成一行一个 `x,y`。
- 长列表在输入框内部滚动；左侧行号随输入框同步滚动。
- 打开 YAML parse 成功后，`source.vertices` 回填为一行一个点的坐标列表。
- `/api/parse` 或 `/api/validate` 返回 `$.shapes[i].source.vertices[j][0]` / `[j][1]` 时，错误定位到坐标列表，并在消息中保留第 `j + 1` 行信息。
- 前端阻断明显结构错误：少于 3 点、空值、非数字、首尾重复、零面积、顺时针点序。
- 点序必须逆时针；违规直接报错，不自动反转。
- 自交、复杂拓扑和 offset 后几何错误最终以后端 validate/preview 为准。
- 后续计划：坐标输入框智能识别更多脚本输出格式，例如空格表格、CSV 块、带括号的点列表。

#### base_shape 倒角输入

base shape 倒角使用三态模式：

- `none`：不写 `fillet` 字段。
- `unified radius`：写 `fillet.radius`。
- `per-corner radii`：写 `fillet.radii`，横向输入半径列表。

逐角半径列表的交互规则：

- direct vertices 模式下，第 `i` 个半径绑定第 `i` 行顶点，依赖坐标列表的逆时针顺序。
- direct vertices 模式下，半径列表必须和当前顶点数量完全一致，数量不匹配时阻止 Apply。
- `source.ref + offset` 模式下，第 `i` 个半径绑定 offset 后的第 `i` 个边界点；前端不预测 offset 后点数，只做数值校验和格式化，点数匹配由 preview/validate 后端校验。
- 半径必须是非负有限数值，允许 `0` 表示该角不倒角。
- 推荐使用横向逗号格式，例如 `1, 2, 0, 3`。
- 兼容换行、分号和 `[1, 2, 0, 3]` 数组格式；`格式化` 后统一显示为横向逗号列表。
- 用户从统一半径切到逐角半径时，如果列表为空，direct vertices 使用当前顶点数展开；ref+offset 尽量使用被引用 direct vertices 的点数展开，否则保持空输入等待用户填写。
- 用户修改顶点数量后，逐角半径不自动补齐或截断；数量不匹配时阻止 Apply。

实施计划：

1. 移除 GUI 对 `source.ref + offset` 的逐角半径禁用逻辑。
2. `readBaseFields()` 在 ref 模式下允许 `fillet.radii`，但不做前端长度校验。
3. 状态提示区区分 direct vertices 的“匹配 N 个顶点”和 ref+offset 的“offset 后由预览校验”。
4. 保持 YAML 协议不变，仍输出标准 `fillet.radii`。
5. 测试覆盖 ref+offset 模式可选择逐角半径、可序列化，并且 direct vertices 的长度硬校验不回退。

## 6. 实时 SVG 预览

右侧预览区始终显示当前 YAML 的 SVG 预览状态。

触发规则：

- 表单修改后 debounce `300-500ms`。
- Open YAML parse 成功并回填表单后 debounce `300-500ms`。
- 手动点击 `Validate` 不应是预览的唯一入口。

状态：

| 状态 | UI |
| --- | --- |
| `idle` | 尚未渲染。 |
| `stale` | YAML 已变化，但新的预览尚未完成；保留旧 SVG，并显示“预览待更新”。 |
| `rendering` | 显示 loading，保留旧 SVG。 |
| `ready` | 显示最新 SVG 和 region count。 |
| `error` | 显示错误摘要，保留旧 SVG 或显示空状态。 |
| `yaml_invalid` | 显示“YAML 有语法/协议错误，预览暂停”。 |

状态转换：

- 表单编辑并成功生成新 YAML 后，如果已有成功预览，立即进入 `stale`。
- debounce 触发 `/api/preview/svg` 后进入 `rendering`。
- 新请求成功并且 `request_id` 仍是最新时进入 `ready`。
- 新请求失败进入 `error`，旧 SVG 可保留但必须标明错误。
- YAML parse/validate 进入 invalid 后，预览状态进入 `yaml_invalid`。

交互：

- `适配视图`
- `放大`
- `缩小`
- 鼠标滚轮缩放可后续再加，第一版不是必须。

SVG 预览不是导出产物，界面不提供保存 SVG。

居中规则：

- SVG 进入固定尺寸 `.svg-stage`，stage 在 preview viewport 中居中。
- 前端挂载 SVG 后必须使用 `preserveAspectRatio="xMidYMid meet"`。
- SVG 不能依赖文档流自然高度定位；否则 Matplotlib 生成的 intrinsic 画布会把图形推到下方。
- `Fit to view` 应重置 pan/zoom，使 SVG 的 `viewBox` 完整显示在 stage 中央。

## 7. 创建/编辑模态框

### 7.1 创建 Via

```text
基于 #0 "source_pad" 创建 Via

name:   [ contact_window ]
layer:  [ 10 ] / [ 0 ]

offsets:
  inner: [ -5 ] um
  outer: [  8 ] um

inner fillet:
  (●) none
  ( ) unified radius [ 1 ] um
  ( ) per-corner radii [ 1, 2, 0, 3 ]

outer fillet:
  (●) none
  ( ) unified radius [ 2 ] um
  ( ) per-corner radii [ 2, 2, 1, 1 ]

[取消] [创建]
```

via 倒角输入规则：

- `inner` 和 `outer` 是两个独立倒角配置，分别写入 `fillet.inner` 和 `fillet.outer`。
- 每一侧都有 `none` / `unified radius` / `per-corner radii` 三种模式。
- `unified radius` 写 `fillet.<side>.radius`。
- `per-corner radii` 写 `fillet.<side>.radii`，推荐横向逗号格式，例如 `1, 2, 0, 3`。
- via 的 inner/outer 都是 offset 后边界；前端不预测边界点数，只校验半径是非负有限数值，长度匹配和几何合法性由 preview/validate 后端校验。
- GUI 默认启用 outer 同心联动。设 `delta = outer_offset - inner_offset`：
  - inner `radius = r` 时，outer 自动填 `radius = r + delta`。
  - inner `radii = [r0, r1, ...]` 时，outer 自动填 `radii = [r0 + delta, r1 + delta, ...]`。
  - inner `none` 时，outer 自动为 `none`。
- 用户手动修改 outer mode/radius/radii 后，outer 进入 override 状态，不再跟随 inner；用户可以重新启用“outer 自动同心”恢复联动。
- 同心联动是 GUI 辅助，不进入 YAML；YAML 只保存计算后的显式 `fillet.outer.radius/radii`。

实施计划：

1. 将 via 现有 inner/outer 半径输入替换为两个独立 fillet side editor。
2. 复用 base shape 的横向 radii 解析、格式化和非负数值校验。
3. YAML serializer 支持 `fillet.inner.radii` 和 `fillet.outer.radii`，同时保留 `radius`。
4. 打开 YAML 时根据 `radius` / `radii` 回填对应 mode 和输入值。
5. 测试覆盖 via inner/outer radii 控件存在、序列化路径存在、旧的 unified radius 不回退。
6. 增加 outer 同心 auto/override 状态；inner 或 offsets 变化时只在 auto 状态下重算 outer。

### 7.2 创建 Rings

```text
基于 #0 "source_pad" 创建 Rings

name:   [ guard_rings ]
layer:  [ 20 ] / [ 0 ]

source:
  (●) vertices
  ( ) source ref + offset

vertices:
  [ 坐标列表输入，格式同 base_shape ]

source ref + offset:
  source ref [ #0 base ]
  source offset [      ] um

count:  [ 3  ]
pitch:  [ 12 ] um
width:  [ 4  ] um

fillet:
  (●) none for all rings
  ( ) concentric from inner fillet
  ( ) configure per ring

concentric from inner fillet:
  base inner:
    ( ) unified radius [ 1 ] um
    ( ) per-corner radii [ 1, 2, 0, 3 ]

只有选择 "configure per ring" 后才显示 per-ring 表格：
  Ring 0: inner (radius) [ 1 ]      outer (radii) [ 2, 2, 1, 1 ]
  Ring 1: inner (none)              outer (radius) [ 14 ]
  Ring 2: inner (radii) [ 3, 4, 4 ] outer (radii) [ 7, 8, 8 ]

[同一倒角应用到全部 rings]

[取消] [创建]
```

`同一倒角应用到全部 rings` 只是单个 rings shape 内的填表快捷操作。它不会创建多个 rings shape，也不会引入新的 YAML 简写协议。

`rings` 倒角写入规则：

- `none for all rings` 模式不写 `fillet` 字段，避免传出与 `count` 不匹配的空数组。
- `concentric from inner fillet` 是 GUI 辅助模式，不进入 YAML。用户配置 base inner 倒角后，GUI 展开为显式 `fillet.rings`：
  - `ring_i.inner.radius = base_radius + i * pitch`
  - `ring_i.outer.radius = base_radius + i * pitch + width`
  - `radii` 模式逐项相加：`ring_i.inner.radii[j] = base_radii[j] + i * pitch`，`ring_i.outer.radii[j] = base_radii[j] + i * pitch + width`
  - 若 base inner 为 none，则不写 `fillet`。
- `configure per ring` 模式写入 `fillet.rings`，长度必须等于 `count`；每个 ring 的 `inner` / `outer` 独立选择 `none` / `radius` / `radii`。
- per-ring 的 `radii` 使用横向列表输入，例如 `1, 2, 4, 4`；前端只校验非负有限数值，逐角数量和 offset 后边界合法性由 preview/validate 判定。
- 用户把 `count` 调大时，新增 ring 行使用空值，并要求用户填写或点击 `同一倒角应用到全部 rings`；前端不静默复制最后一行。
- 用户把 `count` 调小时，超出范围的 per-ring 行进入临时缓存，当前 YAML 只序列化前 `count` 行。
- 从 `configure per ring` 切回 `none for all rings` 时，当前 YAML 删除 `fillet` 字段；临时缓存可以保留在弹层内，方便用户切回。

`rings` source 写入规则：

- `vertices` 模式直接写 `source.vertices`，输入、格式化、长列表滚动和顺逆时针检测与 base_shape 坐标列表一致。
- `source ref + offset` 模式写 `source.ref` 和可选 `source.offset`，下拉只显示已有 base_shape。
- 新建 rings 时如果已有 base_shape，默认使用第一个 base ref；如果没有 base_shape，默认进入 vertices 模式，允许用户直接创建 rings。

实施计划：

1. rings fillet mode 增加 `concentric`。
2. `concentric` 先提供一个 base inner fillet editor，支持 `none` / `radius` / `radii`。
3. serializer 根据 `count/pitch/width` 展开为协议已有的 `fillet.rings` 数组，不新增 YAML 字段。
4. `configure per ring` 暂时保留现有表格能力；后续再升级为每圈 via-style inner/outer editor。
5. 测试覆盖同心 radius/radii 展开和既有 per-ring 行为不回退。

## 8. 主流程

```text
Open app
  │
  ├─ create/edit base_shape through form
  │    ├─ direct vertices
  │    └─ ref + offset copy
  │
  ├─ create via from base_shape
  │    └─ configure inner/outer offset and fillet
  │
  ├─ create rings from base_shape
  │    └─ configure count/pitch/width and optional per-ring fillet
  │
  ├─ generated YAML updates automatically
  │
  ├─ live SVG preview updates automatically from generated YAML
  │
  ├─ validate YAML
  │    └─ map errors to fields
  │
  ├─ save generated YAML
  │    └─ choose .yaml path -> confirm overwrite if needed -> write
  │
  └─ export GDS
       └─ choose .gds path -> confirm overwrite if needed -> export
```

保存/导出路径流程：

```text
click 保存 YAML / 导出 GDS
  -> native save dialog
  -> server returns path_token + path_label + exists
  -> if exists: ask overwrite confirmation
  -> submit save/export with path_token and force flag
  -> success: update status text, clear busy state
```

前端永远不接收真实绝对路径，只展示 `path_label`。

## 9. SID 管理

- 新建 shape 时，`sid = max(existing_sids) + 1`。
- 删除 shape 后不重排 `sid`。
- 引用 shape 时，下拉列表只显示已经存在的 `base_shape`。
- 不允许引用当前 shape 之后的 shape，避免 forward reference。
- `via` 和 `rings` 不可作为 source ref；但 `rings` 可以直接使用 `source.vertices`，不要求先创建 base_shape。

## 10. 字段校验

前端实时校验只做快速反馈；最终阻断以 `/api/validate` 为准。

| 字段 | 规则 | 触发 |
| --- | --- | --- |
| `dbu` | `0.00001 <= dbu <= 1` | input throttle `300ms` + blur |
| `precision` | 若填写，`precision >= dbu` 且 `precision / dbu` 为整数 | input throttle `300ms` + blur |
| `vertices` | 至少 3 个点；空值/非数字/首尾重复/零面积/顺时针立即提示 | input + apply |
| `base_shape.fillet.radii` | direct vertices：数量必须等于顶点数；ref+offset：前端只校验非负有限数值，长度由 preview/validate 校验 | input + apply + preview |
| `layer` | 两个非负整数 | blur |
| `via.offsets.inner/outer` | 有限数值 | blur |
| `rings.count` | 正整数 | blur |
| `rings.pitch` | 正数，且必须满足后端协议 | blur |
| `rings.width` | 正数，且必须满足后端协议 | blur |
| `rings.fillet.rings[].inner/outer.radii` | 非负有限数值列表；数量由 preview/validate 校验 | input + apply + preview |
| `source.ref` | 已存在的 previous base_shape sid | change |

## 11. 错误与操作状态

### 11.1 overwrite confirm

保存 YAML 或导出 GDS 时，如果目标文件已存在：

1. `/api/file/choose-save` 返回 `exists=true`。
2. 前端显示确认对话框，文本包含 `path_label`。
3. 用户确认后调用 `/api/yaml/save` 或 `/api/export/gds`，并传 `force=true`。
4. 用户取消则丢弃 `path_token`，不写文件。

### 11.2 path missing

如果保存/导出路径父目录不存在：

- 显示“目标目录不存在”。
- 不自动创建目录。
- 用户重新选择保存位置。

正常原生保存对话框通常不会返回不存在的父目录，但该错误仍必须处理，以覆盖外部删除目录、网络盘断开等场景。

### 11.3 loading disable

运行以下操作时禁用相关按钮：

- validate
- save YAML
- export GDS
- SVG preview rendering

GDS 导出期间禁用 `Export GDS`，避免重复写同一文件。SVG 渲染期间不禁用编辑，但旧请求结果必须可丢弃。

### 11.4 cancel / timeout

- SVG preview：新请求发出后，旧请求结果按 `request_id` 丢弃。
- GDS export：第一版可以不做真正取消，但需要超时提示，例如 60 秒后显示“导出仍在运行或已超时”。
- 用户关闭窗口时，如果有导出正在运行，提示等待或强制关闭。

### 11.5 dirty state

`dirty = generatedYamlText != lastSavedOrLoadedYamlText`。

触发提示：

- 打开新 YAML 前。
- 关闭窗口前。
- 恢复上一次有效 form draft 前。

保存 YAML 成功后清除 dirty。

### 11.6 token / connection recovery

`path_token` 过期：

- 后端返回 `path_token_expired`。
- 前端显示“保存位置已过期，请重新选择路径”。
- 前端丢弃旧 token，并重新打开保存对话框；不得重用旧路径或要求用户手写路径。

session token 失效：

- 第一版 session token 生命周期等于 GUI 进程生命周期，不做自动续期。
- 如果 API 返回 `session_expired` 或 `unauthorized`，前端显示“会话已失效，请关闭并重新打开程序”。
- 不自动重试写文件操作。

WebView 与 Flask 断连：

- API 请求网络失败或健康检查失败时，显示“本地服务连接中断，请重启程序”。
- 第一版不要求自动重启 Flask；后续可增加轻量心跳和自动恢复。

### 11.7 status text

第一版不提供独立日志区。

顶部 status text 显示最近一条用户需要知道的状态：

- `YAML 已保存`
- `GDS 已导出`
- `校验失败：3 个错误`
- `预览已暂停：YAML 无效`
- `导出失败：目标文件已存在`

详细错误必须显示在对应字段旁；没有字段路径的错误显示在顶部状态旁的可展开错误摘要中。

## 12. PC 端响应与可访问性

第一版不做移动端适配，但必须保证 PC 窗口缩放下可用。

最低响应规则：

- 以 `1280x720` 作为最佳显示目标。
- 以 `640x360` 作为最小支持分辨率。
- 操作区/预览区默认 `1:1`，允许用户拖拽调整。
- 低于最佳尺寸时不重排为移动端，而是让内容区域滚动。
- 坐标列表内部滚动，长列表不挤压模态框。
- YAML 预览模式占用左侧内容区并内部滚动。
- 模态框内容超高时内部滚动。
- splitter 键盘操作：左右箭头调整 `5px`，`Shift + Arrow` 调整 `20px`，`Home` 跳到左侧最小 `35%`，`End` 跳到左侧最大 `65%`。

最低可访问性规则：

- 图标按钮必须有文字或 `aria-label`。
- 表单错误必须出现在对应字段旁边。
- validate 失败后 focus 到第一个错误字段。
- loading 不只靠颜色表达，必须有文字状态。
- 删除、覆盖、关闭未保存配置必须二次确认。
- 错误不能只用红色区分，必须有文本。

## 13. 老版 web_gui 参考与取舍

| 方面 | 老版 web_gui | v2 第一版 GUI |
| --- | --- | --- |
| 协议 | v1 polygon/rings/via 字段 | v2 `base_shape` / `via` / `rings` |
| rings 参数 | `ring_width` / `ring_space` 支持字符串规则 | 固定 `count` / `pitch` / `width` |
| 派生关系 | linkage、继承、override | 只使用 `source.ref` |
| 预览 | 无正式实时预览 | 实时 SVG 预览 |
| 输出 | YAML/GDS 以及旧预览路径 | GUI 产物仅 YAML/GDS |
| 前端依赖 | jQuery/Bootstrap/JSONEditor | 本地 vendored JS + 自定义 CSS |

老版复杂性不进入第一版 GUI。需要复杂 rings 组合时，用户可以显式创建多个普通 `rings` shape；GUI 不提供批量创建入口。
