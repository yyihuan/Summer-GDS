# Frontend Design System v1.5

文档版本：v1.5
日期：2026-05-25
状态：方案设计

---

## 1. 设计方向

Summer GDS GUI 是 PC 端工程工具，不做网页营销感，也不做移动端优先。

视觉目标：

- **像仪器面板，不像后台模板**：信息密度高，但每块区域边界清楚。
- **预览优先**：右侧 SVG 预览是持续反馈，不是导出入口。
- **YAML 可见但不压迫用户**：普通用户只需要操作表单；YAML 作为生成结果、保存格式和调试视图存在。
- **错误可定位**：错误必须出现在字段旁、卡片摘要和顶部状态中。
- **本地可信**：不使用 CDN，不出现远程服务感。

关键词：

- precise
- calm
- technical
- local-first
- inspection-grade

不使用：

- 紫蓝渐变默认主题。
- 大面积阴影卡片。
- 营销页 hero。
- 装饰性 blob / wave。
- 仅靠图标表达操作。

### 1.1 Implementation Spec

这是 `$design-html` fallback 下的实现规格，后续编码以此为页面结构依据。

| 项 | 规格 |
| --- | --- |
| Layout type | Desktop engineering workspace: topbar + resizable two-pane split. |
| Primary task | Build a v2 YAML config through forms, not by typing YAML. |
| Left pane | Builder-first workspace: mode switch, compact shape list, readonly YAML preview mode, Global settings modal/drawer. |
| Right pane | Live SVG viewport with centered fit and preview status. |
| Color direction | Warm instrument panel: stone background, off-white panels, green primary, copper accent, red danger. |
| Type | System UI sans for controls, monospace for coordinates and generated YAML. |
| Density | High-density engineering UI; avoid large blank marketing sections. |
| Motion | Only functional transitions: busy state, splitter hover, preview refresh. |
| Dependencies | No CDN, no Tailwind/Bootstrap, no npm build chain in first version. |

Component inventory:

- Topbar document actions: Open YAML, Save YAML, Validate, Export GDS.
- Document state pills: dirty, validation, preview, export.
- Mode switch: `构建器` / `YAML 预览`; visually button-like, not a tab strip.
- Global settings modal/drawer: `dbu`, optional `precision`, fixed `unit`, `top_cell`, readonly imported `gds.output`.
- Shape action bar: `+ Base Shape`, `+ Via`, `+ Rings`.
- Shape cards: compact summary + explicit Edit/Delete/Create Via/Create Rings actions.
- Coordinate list editor: code-like point list with line numbers, formatting, and strict orientation validation.
- Base fillet editor: `none` / unified radius / horizontal per-corner radii list for direct vertices.
- Create Via modal: source base shape, offsets, layer, inner/outer fillet.
- Create Rings modal: source base shape, count/pitch/width, optional per-ring inner/outer fillet.
- YAML preview mode: readonly generated YAML text, visible only when selected.
- SVG stage: fixed viewport, centered SVG, Fit/Zoom controls.

## 2. 画布与布局

### 2.1 分辨率目标

| 项 | 值 |
| --- | --- |
| 最佳设计目标 | `1280x720` |
| 最小支持分辨率 | `640x360` |
| 默认比例 | 操作区 : 预览区 = `1:1` |
| splitter 范围 | `35:65` 到 `65:35` |

布局策略：

- `body` 固定占满窗口。
- app 使用纵向 grid：topbar + main。
- main 使用横向 grid：workspace + preview。
- 低于 `1280x720` 不重排为移动端，只允许内容区滚动。
- 低于 `640x360` 不保证完整可用，只保证不崩溃。

### 2.2 区域职责

```text
┌ app ──────────────────────────────────────────────────────┐
│ topbar: product, document state, actions, status           │
├───────────────────────────────┬───────────────────────────┤
│ workspace                      │ preview-pane              │
│ ├─ mode switch + global button │ ├─ preview-toolbar        │
│ ├─ shape action bar            │ └─ centered svg viewport  │
│ └─ shape list OR YAML preview  │                           │
└───────────────────────────────┴───────────────────────────┘
```

独立日志区不进入第一版。状态放在 topbar status 和字段/预览错误态里。

## 3. CSS Tokens

第一版 `style.css` 必须从 CSS custom properties 开始。不要把颜色、间距、圆角散落在组件里。

```css
:root {
  color-scheme: light;

  /* type */
  --font-ui: "Aptos", "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "Cascadia Code", monospace;
  --font-size-10: 10px;
  --font-size-11: 11px;
  --font-size-12: 12px;
  --font-size-13: 13px;
  --font-size-15: 15px;
  --font-size-18: 18px;
  --line-tight: 1.2;
  --line-normal: 1.45;

  /* surface */
  --color-app: #e7e1d4;
  --color-panel: #f8f4ea;
  --color-panel-2: #eee7da;
  --color-ink: #1e241f;
  --color-muted: #667067;
  --color-border: #b9ad9b;
  --color-border-strong: #8c7f6a;

  /* accents */
  --color-primary: #2f5d50;
  --color-primary-ink: #f7fbf7;
  --color-accent: #b56f2a;
  --color-focus: #1f6f8b;
  --color-danger: #9f2d24;
  --color-warning: #94630b;
  --color-success: #2f6b3f;

  /* preview layer colors */
  --layer-1: #2f5d50;
  --layer-2: #b56f2a;
  --layer-3: #596b9a;
  --layer-hole: #f8f4ea;

  /* spacing */
  --space-2: 2px;
  --space-4: 4px;
  --space-6: 6px;
  --space-8: 8px;
  --space-10: 10px;
  --space-12: 12px;
  --space-16: 16px;
  --space-20: 20px;

  /* shape */
  --radius-4: 4px;
  --radius-6: 6px;
  --radius-8: 8px;
  --border-thin: 1px;
  --border-thick: 2px;

  /* layout */
  --topbar-height: 56px;
  --min-app-width: 640px;
  --min-app-height: 360px;
  --ideal-app-width: 1280px;
  --ideal-app-height: 720px;
}
```

Font policy:

- 第一版优先使用系统自带字体，避免额外字体文件打包。
- 如果后续引入字体文件，必须放在 `v2/src/summer_gds/gui/static/vendor/fonts/`，不能使用 Google Fonts 或 CDN。
- 坐标列表输入、横向逐角半径列表、行号和 YAML 预览使用 monospace，按钮、标签和状态使用 UI sans。

## 4. HTML Skeleton

`index.html` 第一版应保持语义清楚，避免把布局全写在 JS 中。

```html
<body>
  <div id="app" class="app-shell" data-yaml-status="valid" data-preview-status="ready">
    <header class="topbar" aria-label="应用工具栏">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <div>
          <h1>Summer GDS</h1>
          <p>本地版图工作台</p>
        </div>
      </div>

      <div class="document-state" aria-live="polite">
        <span class="state-pill" data-state="dirty">YAML 已修改</span>
        <span class="state-pill" data-state="ready">预览已就绪</span>
        <span class="state-pill" data-state="idle">GDS 未导出</span>
      </div>

      <nav class="top-actions" aria-label="文档操作">
        <button class="button button-secondary" type="button">打开 YAML</button>
        <button class="button button-secondary" type="button">保存 YAML</button>
        <button class="button button-secondary" type="button">校验</button>
        <button class="button button-primary" type="button">导出 GDS</button>
      </nav>

      <div class="status-text" role="status" aria-live="polite">
        预览已更新
      </div>
    </header>

    <main class="app-main">
      <section class="workspace-pane" aria-label="配置编辑器">
        <div class="workspace-switcher" aria-label="工作区模式">
          <button class="mode-button is-active" type="button" aria-pressed="true">构建器</button>
          <button class="mode-button" type="button" aria-pressed="false">YAML 预览</button>
          <button class="button button-secondary global-settings-button" type="button">全局设置</button>
        </div>

        <div class="shape-action-bar" aria-label="创建图形">
          <button class="button button-secondary" type="button">+ 基础图形</button>
          <button class="button button-secondary" type="button">+ Via</button>
          <button class="button button-secondary" type="button">+ Rings</button>
        </div>

        <section class="workspace-content" data-mode="builder">
          <div class="shape-list" aria-label="图形列表">
            <!-- compact shape cards -->
          </div>

          <section class="yaml-preview-panel" aria-label="生成的 YAML" hidden>
            <textarea class="textarea generated-yaml" data-kind="yaml" readonly></textarea>
          </section>
        </section>
      </section>

      <div class="splitter" role="separator" aria-orientation="vertical" tabindex="0"></div>

      <aside class="preview-pane" aria-label="实时 SVG 预览">
        <div class="preview-toolbar">
          <h2>SVG 预览</h2>
          <div class="toolbar-actions">
            <button class="button button-ghost" type="button">适配</button>
            <button class="button button-ghost" type="button">缩小</button>
            <button class="button button-ghost" type="button">放大</button>
          </div>
        </div>

        <div class="preview-viewport" data-preview-state="ready">
          <div class="svg-stage" aria-label="版图几何预览">
            <!-- server-returned svg_text mounted here -->
          </div>
        </div>
      </aside>
    </main>
  </div>
</body>
```

## 5. Base CSS Layout

```css
html,
body {
  width: 100%;
  height: 100%;
  margin: 0;
  overflow: hidden;
  background: var(--color-app);
  color: var(--color-ink);
  font-family: var(--font-ui);
  font-size: var(--font-size-13);
}

.app-shell {
  min-width: var(--min-app-width);
  min-height: var(--min-app-height);
  width: 100vw;
  height: 100vh;
  display: grid;
  grid-template-rows: var(--topbar-height) minmax(0, 1fr);
  background:
    linear-gradient(90deg, rgba(47, 93, 80, 0.08) 1px, transparent 1px),
    linear-gradient(0deg, rgba(47, 93, 80, 0.06) 1px, transparent 1px),
    var(--color-app);
  background-size: 24px 24px;
}

.topbar {
  display: grid;
  grid-template-columns: minmax(190px, 260px) minmax(260px, 1fr) auto minmax(180px, 260px);
  align-items: center;
  gap: var(--space-12);
  padding: 0 var(--space-12);
  border-bottom: var(--border-thick) solid var(--color-border-strong);
  background: rgba(248, 244, 234, 0.94);
}

.app-main {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(224px, 1fr) 8px minmax(224px, 1fr);
}

.workspace-pane,
.preview-pane {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--color-panel);
}

.workspace-pane {
  display: grid;
  grid-template-rows: 36px 38px minmax(0, 1fr);
  border-right: var(--border-thin) solid var(--color-border);
}

.splitter {
  cursor: col-resize;
  background: linear-gradient(90deg, var(--color-border), var(--color-panel-2));
}

.preview-pane {
  display: grid;
  grid-template-rows: 40px minmax(0, 1fr);
}

.preview-viewport {
  min-height: 0;
  padding: var(--space-12);
  overflow: hidden;
  background: #d8d0c0;
}

.svg-stage {
  min-width: 220px;
  min-height: 220px;
  height: 100%;
  display: grid;
  place-items: center;
  border: var(--border-thin) solid var(--color-border-strong);
  background: var(--color-panel);
}

.svg-stage svg {
  display: block;
  max-width: 100%;
  max-height: 100%;
}
```

## 6. Components

### 6.1 Buttons

Button hierarchy:

- `button-primary`: irreversible or main output action, only `Export GDS`.
- `button-secondary`: file and validation operations.
- `button-ghost`: low-risk viewport actions.
- `button-danger`: destructive actions such as delete shape.

```css
.button {
  min-height: 30px;
  padding: 0 var(--space-12);
  border: var(--border-thin) solid var(--color-border-strong);
  border-radius: var(--radius-4);
  font: inherit;
  font-weight: 650;
  cursor: pointer;
  background: var(--color-panel);
  color: var(--color-ink);
}

.button:hover {
  border-color: var(--color-primary);
}

.button:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.button-primary {
  background: var(--color-primary);
  color: var(--color-primary-ink);
}

.button-danger {
  border-color: var(--color-danger);
  color: var(--color-danger);
}
```

### 6.2 Mode Switch

```css
.workspace-switcher {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-8);
  background: var(--color-panel-2);
  border-bottom: var(--border-thin) solid var(--color-border);
}

.mode-button {
  min-height: 26px;
  padding: 0 var(--space-10, 10px);
  border: var(--border-thin) solid var(--color-border);
  border-radius: var(--radius-4);
  background: rgba(248, 244, 234, 0.65);
  color: var(--color-muted);
  font-size: var(--font-size-12);
  font-weight: 750;
}

.mode-button.is-active,
.mode-button[aria-pressed="true"] {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-primary-ink);
}

.global-settings-button {
  margin-left: auto;
  min-height: 26px;
  font-size: var(--font-size-12);
}
```

Rules:

- Mode switch is not a WAI-ARIA tabset; it is a pair of persistent view buttons.
- Switching to `YAML 预览` replaces the shape list with readonly YAML.
- `全局设置` opens a modal/drawer and must not consume persistent left-pane height.

### 6.3 Shape Action Bar

```css
.shape-action-bar {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-6) var(--space-8);
  border-bottom: var(--border-thin) solid var(--color-border);
  background: var(--color-panel);
}
```

### 6.4 Shape Cards

Shape cards are dense. Do not use large card shadows.

```html
<article class="shape-card" data-shape-type="base_shape" data-error="false">
  <header class="shape-card-header">
    <div>
      <span class="shape-id">#0</span>
      <strong>source_pad</strong>
      <span class="type-badge">base_shape</span>
    </div>
    <div class="shape-actions">
      <button class="button button-ghost">Edit</button>
      <button class="button button-danger">Delete</button>
    </div>
  </header>
  <dl class="shape-summary">
    <div><dt>Layer</dt><dd>[1, 0]</dd></div>
    <div><dt>Vertices</dt><dd>4</dd></div>
    <div><dt>Fillet</dt><dd>none</dd></div>
  </dl>
</article>
```

```css
.shape-list {
  min-height: 0;
  overflow: auto;
  padding: var(--space-8);
}

.shape-list .shape-card + .shape-card {
  margin-top: var(--space-8);
}

.shape-card {
  border: var(--border-thin) solid var(--color-border);
  border-left: 4px solid var(--color-primary);
  background: var(--color-panel);
  font-size: var(--font-size-12);
}

.shape-card[data-shape-type="via"] {
  border-left-color: var(--color-accent);
}

.shape-card[data-shape-type="rings"] {
  border-left-color: #596b9a;
}

.shape-card[data-error="true"] {
  border-color: var(--color-danger);
}

.shape-card-header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-8);
  padding: var(--space-6) var(--space-8);
  border-bottom: var(--border-thin) solid var(--color-border);
}

.shape-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
  margin: 0;
  padding: var(--space-6) var(--space-8);
}

.shape-summary dt {
  color: var(--color-muted);
  font-size: var(--font-size-11);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.shape-summary dd {
  margin: 0;
  font-family: var(--font-mono);
}
```

### 6.5 Forms

```css
.field {
  display: grid;
  gap: var(--space-4);
}

.field-label {
  font-size: var(--font-size-12);
  font-weight: 700;
  color: var(--color-muted);
}

.input,
.textarea,
.select {
  min-height: 30px;
  border: var(--border-thin) solid var(--color-border);
  border-radius: var(--radius-4);
  padding: 0 var(--space-8);
  background: #fffdf7;
  color: var(--color-ink);
  font: inherit;
}

.input[data-kind="number"],
.textarea[data-kind="yaml"],
.vertex-table input {
  font-family: var(--font-mono);
}

.field[data-error="true"] .input,
.field[data-error="true"] .textarea,
.field[data-error="true"] .select {
  border-color: var(--color-danger);
}

.field-error {
  color: var(--color-danger);
  font-size: var(--font-size-12);
}
```

### 6.6 YAML Preview Mode

Generated YAML is a visible artifact, not the primary editor. It appears only when the user selects `YAML 预览`.

```html
<section class="yaml-preview-panel" aria-label="Generated YAML">
  <header class="panel-toolbar">
    <h2>YAML 预览</h2>
    <span class="state-pill" data-state="readonly">Readonly</span>
  </header>
  <textarea class="textarea generated-yaml" data-kind="yaml" readonly></textarea>
</section>
```

```css
.yaml-preview-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: 36px minmax(0, 1fr);
}

.generated-yaml {
  min-height: 0;
  resize: none;
  overflow: auto;
  white-space: pre;
}
```

Rules:

- First version keeps this view readonly.
- This panel is not permanently mounted at the bottom of the builder view.
- Save YAML writes exactly this generated YAML text.
- Open YAML parse success hydrates the form and then refreshes this view.
- Invalid imported YAML is reported as an import error and must not replace the current form draft.

### 6.7 Preview States

```css
.preview-viewport[data-preview-state="rendering"] .svg-stage {
  opacity: 0.65;
}

.preview-viewport[data-preview-state="stale"] .svg-stage {
  opacity: 0.78;
  filter: saturate(0.75);
}

.preview-viewport[data-preview-state="error"] {
  border-top: 3px solid var(--color-danger);
}

.preview-viewport[data-preview-state="yaml_invalid"] {
  border-top: 3px solid var(--color-warning);
}
```

SVG mount rules:

- The returned SVG must be mounted inside `.svg-stage`, never directly into the viewport.
- JS must set `preserveAspectRatio="xMidYMid meet"` on the mounted root SVG.
- If the SVG has fixed `width`/`height`, CSS still controls display via `max-width` and `max-height`.
- The geometry should visually sit in the center of the stage after initial render and after `Fit`.

UI text policy:

- 用户可见文案使用简体中文。
- `data-*` 值、API 状态值和 JS enum 使用英文稳定值，便于测试和样式选择。
- 如果后续需要多语言，文案集中到一个 copy map；第一版不引入完整 i18n 框架。

Preview copy:

| State | Text |
| --- | --- |
| `idle` | `尚未生成预览。` |
| `stale` | `YAML 已变化，预览待更新。` |
| `rendering` | `正在生成预览...` |
| `ready` | `预览已更新。` |
| `error` | `预览失败，请修正标记字段。` |
| `yaml_invalid` | `YAML 无效，预览已暂停。` |

## 7. State Attributes

Use data attributes for cross-component styling. Do not derive visual state only from class names.

| Attribute | Values | Owner |
| --- | --- | --- |
| `data-yaml-status` | `valid`, `invalid`, `syncing` | `.app-shell` |
| `data-preview-status` | `idle`, `stale`, `rendering`, `ready`, `error`, `yaml_invalid` | `.app-shell` |
| `data-dirty` | `true`, `false` | `.app-shell` |
| `data-busy` | `true`, `false` | `.app-shell` |
| `data-shape-type` | `base_shape`, `via`, `rings` | `.shape-card` |
| `data-error` | `true`, `false` | `.field`, `.shape-card` |

State combination rules:

- `data-yaml-status="invalid"` requires `data-preview-status="yaml_invalid"`.
- `data-yaml-status="syncing"` may pair with `data-preview-status="stale"` or `rendering`, but not `ready`.
- `data-busy="true"` must be accompanied by visible status text explaining the active operation.
- `data-preview-status="stale"` may show old SVG, but status text must make the staleness explicit.
- `data-preview-status="ready"` means `generatedYamlText` and the latest accepted preview request are in sync.

## 8. Accessibility Rules

- All icon-like controls still need visible text in first version.
- `status-text` uses `role="status"` and `aria-live="polite"`.
- Validation summary should link/focus the first field with `data-error="true"`.
- Modal dialogs use `role="dialog"`, `aria-modal="true"`, and focus trapping.
- Splitter uses `role="separator"`, `aria-orientation="vertical"`, `tabindex="0"`, and keyboard support: Arrow keys adjust `5px`, `Shift + Arrow` adjusts `20px`, `Home` jumps to left min `35%`, `End` jumps to left max `65%`.
- Buttons disabled during save/export must still expose a text reason in status.

## 9. Implementation Rules

- `style.css` contains all visual styles and CSS tokens.
- `app.js` owns state and API calls.
- `components.js` may provide string/template helpers, but must not hide business rules.
- No inline styles except dynamic splitter width and SVG pan/zoom transforms.
- No remote fonts, scripts, styles, or images.
- Do not introduce Tailwind, Bootstrap, or npm build chain in first version.

## 10. First Implementation Checklist

- `index.html` includes semantic shell from this document.
- `style.css` starts with the token block.
- App renders correctly at `1280x720`.
- App remains usable with scrollbars at `640x360`.
- SVG preview pane and workspace pane start at `1:1`.
- Topbar has no wrapping at `1280x720`.
- Shape cards show `base_shape`, `via`, and `rings` with distinct left rail colors.
- YAML preview is readonly, appears only in `YAML 预览` mode, and is not a bottom panel inside the builder.
- SVG preview is centered in `.svg-stage`, not aligned to top or bottom by intrinsic SVG size.
- Preview stale state visibly says the previous SVG is outdated.
- User-visible UI copy is Simplified Chinese; internal state values remain stable English strings.
- Splitter keyboard controls obey the documented `5px` / `20px` / `Home` / `End` behavior.
- All destructive actions have visible text and confirmation.
- No CDN references exist in production HTML.
