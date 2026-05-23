# Frontend Design System v1

文档版本：v1.0
日期：2026-05-24
状态：方案设计

---

## 1. 设计方向

Summer GDS GUI 是 PC 端工程工具，不做网页营销感，也不做移动端优先。

视觉目标：

- **像仪器面板，不像后台模板**：信息密度高，但每块区域边界清楚。
- **预览优先**：右侧 SVG 预览是持续反馈，不是导出入口。
- **YAML 可见但不压迫用户**：普通用户主要用表单，高级用户可直接改 YAML。
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
│ ├─ tabs                        │ ├─ preview-toolbar        │
│ └─ active panel                │ └─ svg viewport           │
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
- 如果后续引入字体文件，必须放在 `v2/gui/static/vendor/fonts/`，不能使用 Google Fonts 或 CDN。
- YAML 和坐标表格使用 monospace，按钮、标签和状态使用 UI sans。

## 4. HTML Skeleton

`index.html` 第一版应保持语义清楚，避免把布局全写在 JS 中。

```html
<body>
  <div id="app" class="app-shell" data-yaml-status="valid" data-preview-status="ready">
    <header class="topbar" aria-label="Application toolbar">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <div>
          <h1>Summer GDS</h1>
          <p>YAML to GDS layout generator</p>
        </div>
      </div>

      <div class="document-state" aria-live="polite">
        <span class="state-pill" data-state="dirty">YAML modified</span>
        <span class="state-pill" data-state="ready">Preview ready</span>
        <span class="state-pill" data-state="idle">GDS not exported</span>
      </div>

      <nav class="top-actions" aria-label="Document actions">
        <button class="button button-secondary" type="button">Open YAML</button>
        <button class="button button-secondary" type="button">Save YAML</button>
        <button class="button button-secondary" type="button">Validate</button>
        <button class="button button-primary" type="button">Export GDS</button>
      </nav>

      <div class="status-text" role="status" aria-live="polite">
        Preview updated
      </div>
    </header>

    <main class="app-main">
      <section class="workspace-pane" aria-label="Configuration editor">
        <div class="tabs" role="tablist" aria-label="Editor sections">
          <button class="tab is-active" role="tab" aria-selected="true">Global</button>
          <button class="tab" role="tab" aria-selected="false">Shapes</button>
          <button class="tab" role="tab" aria-selected="false">YAML</button>
        </div>

        <section class="panel-stack">
          <!-- active panel rendered here -->
        </section>
      </section>

      <div class="splitter" role="separator" aria-orientation="vertical" tabindex="0"></div>

      <aside class="preview-pane" aria-label="Live SVG preview">
        <div class="preview-toolbar">
          <h2>SVG Preview</h2>
          <div class="toolbar-actions">
            <button class="button button-ghost" type="button">Fit</button>
            <button class="button button-ghost" type="button">Zoom -</button>
            <button class="button button-ghost" type="button">Zoom +</button>
          </div>
        </div>

        <div class="preview-viewport" data-preview-state="ready">
          <div class="svg-stage" aria-label="Rendered geometry preview">
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
  grid-template-rows: 40px minmax(0, 1fr);
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
  overflow: auto;
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

### 6.2 Tabs

```css
.tabs {
  display: flex;
  align-items: end;
  gap: var(--space-4);
  padding: var(--space-6) var(--space-8) 0;
  background: var(--color-panel-2);
  border-bottom: var(--border-thin) solid var(--color-border);
}

.tab {
  min-height: 32px;
  padding: 0 var(--space-12);
  border: var(--border-thin) solid transparent;
  border-bottom: 0;
  border-radius: var(--radius-6) var(--radius-6) 0 0;
  background: transparent;
  color: var(--color-muted);
  font-weight: 700;
}

.tab.is-active {
  background: var(--color-panel);
  border-color: var(--color-border);
  color: var(--color-ink);
}
```

### 6.3 Shape Cards

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
.shape-card {
  border: var(--border-thin) solid var(--color-border);
  border-left: 4px solid var(--color-primary);
  background: var(--color-panel);
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
  padding: var(--space-8);
  border-bottom: var(--border-thin) solid var(--color-border);
}

.shape-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-8);
  margin: 0;
  padding: var(--space-8);
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

### 6.4 Forms

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

### 6.5 Preview States

```css
.preview-viewport[data-preview-state="rendering"] .svg-stage {
  opacity: 0.65;
}

.preview-viewport[data-preview-state="error"] {
  border-top: 3px solid var(--color-danger);
}

.preview-viewport[data-preview-state="yaml_invalid"] {
  border-top: 3px solid var(--color-warning);
}
```

Preview copy:

| State | Text |
| --- | --- |
| `idle` | `Preview has not rendered yet.` |
| `rendering` | `Rendering preview...` |
| `ready` | `Preview updated.` |
| `error` | `Preview failed. Fix the highlighted fields.` |
| `yaml_invalid` | `YAML is invalid. Preview paused.` |

## 7. State Attributes

Use data attributes for cross-component styling. Do not derive visual state only from class names.

| Attribute | Values | Owner |
| --- | --- | --- |
| `data-yaml-status` | `valid`, `invalid`, `syncing` | `.app-shell` |
| `data-preview-status` | `idle`, `rendering`, `ready`, `error`, `yaml_invalid` | `.app-shell` |
| `data-dirty` | `true`, `false` | `.app-shell` |
| `data-busy` | `true`, `false` | `.app-shell` |
| `data-shape-type` | `base_shape`, `via`, `rings` | `.shape-card` |
| `data-error` | `true`, `false` | `.field`, `.shape-card` |

## 8. Accessibility Rules

- All icon-like controls still need visible text in first version.
- `status-text` uses `role="status"` and `aria-live="polite"`.
- Validation summary should link/focus the first field with `data-error="true"`.
- Modal dialogs use `role="dialog"`, `aria-modal="true"`, and focus trapping.
- Splitter uses `role="separator"`, `aria-orientation="vertical"`, `tabindex="0"`, and keyboard arrow support.
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
- All destructive actions have visible text and confirmation.
- No CDN references exist in production HTML.
