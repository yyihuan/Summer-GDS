# 前端交互与页面设计 v2.1

文档版本：v2.1
日期：2026-05-24
状态：方案设计

---

## 1. 设计目标

- 用户通过可视化表单编辑 YAML v2 配置，无需手写 YAML。
- 支持 `base_shape`、`via`、`rings` 三类公开 shape。
- YAML 是唯一持久化真源；表单、实时 SVG 预览和错误定位都从 YAML 派生。
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
│ [Open YAML] [Save YAML] [Validate] [Export GDS]                status text  │
├──────────────────────────────────────────┬─────────────────────────────────┤
│ 操作区 / YAML 编辑区                       │ 实时 SVG 预览区                    │
│                                          │                                 │
│ [Global] [Shapes] [YAML]                 │ ┌─ SVG Preview ───────────────┐ │
│                                          │ │ [Fit] [Zoom +] [Zoom -]     │ │
│  当前 Tab 内容                            │ │                             │ │
│                                          │ │        live SVG             │ │
│                                          │ │                             │ │
│                                          │ └─────────────────────────────┘ │
└──────────────────────────────────────────┴─────────────────────────────────┘
```

布局规则：

- 最佳设计目标：标准 16:9 的 `1280x720`。
- 最小支持分辨率：`640x360`。低于最佳尺寸时允许横向/纵向滚动，不做移动端重排。
- 操作区和预览区初始比例为 `1:1`。
- 用户可以拖拽中间 splitter 调整比例，第一版限制在 `35:65` 到 `65:35`。
- 顶点表格和 YAML 编辑器内部滚动，不挤压整页。
- 模态框最大高度 `80vh`，内容区滚动。
- 第一版取消独立日志区。状态、错误和成功提示显示在顶部 status text、字段旁错误和预览错误态中。

## 4. 顶部操作

| 操作 | 行为 |
| --- | --- |
| `Open YAML` | 打开原生文件对话框，读取 `.yaml`/`.yml`。如果当前 dirty，先确认是否丢弃未保存修改。 |
| `Save YAML` | 打开原生保存对话框选择路径，必要时确认覆盖，然后保存当前 YAML。 |
| `Validate` | 调 `/api/validate`，显示字段错误和顶部状态。 |
| `Export GDS` | 打开原生保存对话框选择 `.gds` 路径，必要时确认覆盖，然后导出。 |

不提供：

- `Export PNG`
- `Export SVG`
- `Download preview`

## 5. Tab 面板

### 5.1 Global Tab

编辑 YAML 的 `global` 和 GDS 必要配置。

```text
┌─ global ──────────────────────────────┐
│ dbu:       [ 0.001    ]  (0.00001~1)  │
│ precision: [          ]  optional     │
│ unit:       um (fixed)                │
└───────────────────────────────────────┘

┌─ gds ─────────────────────────────────┐
│ top_cell:  [ TOP         ]            │
│ output:    managed by Export GDS      │
└───────────────────────────────────────┘
```

说明：

- `unit` 第一版固定为 `um`。
- `top_cell` 是 GDS 导出必需字段。
- GUI 导出路径不依赖 `gds.output` 输入框；用户点击 `Export GDS` 时选择保存位置。
- 如果加载的 YAML 已有 `gds.output`，YAML 编辑器保留该字段，并在 Global Tab 中只读展示为 `CLI default output`。
- 表单规范化写回 YAML 时不主动新增 `gds.output`。
- 如果用户在 YAML Tab 手动删除 `gds.output`，GUI 保存 YAML 时不恢复它；GUI 导出 GDS 始终使用保存对话框路径。

### 5.2 Shapes Tab

核心编辑区。顶部只提供添加基础图形：

```text
[+ Add base_shape]
```

`via` 和 `rings` 必须从某个已有 `base_shape` 卡片触发创建，以保证 `source.ref` 合法。

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
  X       Y
  [0]     [0]     [delete row]
  [100]   [0]
  [100]   [80]
  [0]     [80]
  [+ Add point]

fillet:
  (●) none
  ( ) arc radius [ 2 ] um
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

### 5.3 YAML Tab

YAML 编辑器展示并编辑完整 YAML。

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
- YAML 手动编辑成功 parse 后，同步回表单。
- YAML 手动编辑失败时，进入 `yaml_invalid` 状态。
- `yaml_invalid` 状态下，保留用户文本，禁用预览和 GDS 导出。
- 用户可以继续修 YAML，也可以恢复到上一次有效 YAML。

## 6. 实时 SVG 预览

右侧预览区始终显示当前 YAML 的 SVG 预览状态。

触发规则：

- 表单修改后 debounce `300-500ms`。
- YAML 编辑器 parse 成功后 debounce `300-500ms`。
- 手动点击 `Validate` 不应是预览的唯一入口。

状态：

| 状态 | UI |
| --- | --- |
| `idle` | 尚未渲染。 |
| `rendering` | 显示 loading，保留旧 SVG。 |
| `ready` | 显示最新 SVG 和 region count。 |
| `error` | 显示错误摘要，保留旧 SVG 或显示空状态。 |
| `yaml_invalid` | 显示“YAML 有语法/协议错误，预览暂停”。 |

交互：

- `Fit to view`
- `Zoom +`
- `Zoom -`
- 鼠标滚轮缩放可后续再加，第一版不是必须。

SVG 预览不是导出产物，界面不提供保存 SVG。

## 7. 创建/编辑模态框

### 7.1 创建 Via

```text
Create Via based on #0 "source_pad"

name:   [ contact_window ]
layer:  [ 10 ] / [ 0 ]

offsets:
  inner: [ -5 ] um
  outer: [  8 ] um

inner fillet:
  (●) none
  ( ) arc radius [ 1 ] um

outer fillet:
  (●) none
  ( ) arc radius [ 2 ] um

[Cancel] [Create]
```

### 7.2 创建 Rings

```text
Create Rings based on #0 "source_pad"

name:   [ guard_rings ]
layer:  [ 20 ] / [ 0 ]

count:  [ 3  ]
pitch:  [ 12 ] um
width:  [ 4  ] um

fillet:
  (●) none for all rings
  ( ) configure per ring

Ring 0: inner [ 1 ] outer [ 2 ]
Ring 1: inner [ 1 ] outer [ 2 ]
Ring 2: inner [ 1 ] outer [ 2 ]

[Apply same fillet to all rings]

[Cancel] [Create]
```

`Apply same fillet to all rings` 只是单个 rings shape 内的填表快捷操作。它不会创建多个 rings shape，也不会引入新的 YAML 简写协议。

## 8. 主流程

```text
Open app
  │
  ├─ create/edit base_shape
  │    ├─ direct vertices
  │    └─ ref + offset copy
  │
  ├─ create via from base_shape
  │    └─ configure inner/outer offset and fillet
  │
  ├─ create rings from base_shape
  │    └─ configure count/pitch/width and optional per-ring fillet
  │
  ├─ live SVG preview updates automatically
  │
  ├─ validate YAML
  │    └─ map errors to fields
  │
  ├─ save YAML
  │    └─ choose .yaml path -> confirm overwrite if needed -> write
  │
  └─ export GDS
       └─ choose .gds path -> confirm overwrite if needed -> export
```

保存/导出路径流程：

```text
click Save YAML / Export GDS
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
- `via` 和 `rings` 不可作为 source ref。

## 10. 字段校验

前端实时校验只做快速反馈；最终阻断以 `/api/validate` 为准。

| 字段 | 规则 | 触发 |
| --- | --- | --- |
| `dbu` | `0.00001 <= dbu <= 1` | blur |
| `precision` | 若填写，`precision >= dbu` 且 `precision / dbu` 为整数 | blur |
| `vertices` | 至少 3 个点；明显空值/非数字立即提示 | blur |
| `layer` | 两个非负整数 | blur |
| `via.offsets.inner/outer` | 有限数值 | blur |
| `rings.count` | 正整数 | blur |
| `rings.pitch` | 正数，且必须满足后端协议 | blur |
| `rings.width` | 正数，且必须满足后端协议 | blur |
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

`dirty = currentYamlText != lastSavedOrLoadedYamlText`。

触发提示：

- 打开新 YAML 前。
- 关闭窗口前。
- 恢复上一次有效 YAML 前。

保存 YAML 成功后清除 dirty。

### 11.6 status text

第一版不提供独立日志区。

顶部 status text 显示最近一条用户需要知道的状态：

- `YAML saved`
- `GDS exported`
- `Validation failed: 3 errors`
- `Preview paused: YAML invalid`
- `Export failed: output exists`

详细错误必须显示在对应字段旁；没有字段路径的错误显示在顶部状态旁的可展开错误摘要中。

## 12. PC 端响应与可访问性

第一版不做移动端适配，但必须保证 PC 窗口缩放下可用。

最低响应规则：

- 以 `1280x720` 作为最佳显示目标。
- 以 `640x360` 作为最小支持分辨率。
- 操作区/预览区默认 `1:1`，允许用户拖拽调整。
- 低于最佳尺寸时不重排为移动端，而是让内容区域滚动。
- 顶点表格横向滚动。
- YAML 编辑器固定高度并内部滚动。
- 模态框内容超高时内部滚动。

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
