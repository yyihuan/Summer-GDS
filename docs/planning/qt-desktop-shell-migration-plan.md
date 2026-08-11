# Qt 桌面壳迁移计划

- 文档版本：v1.3
- 日期：2026-07-30
- 状态：第二轮评审及综合核对意见已全部处置；实施就绪，Phase 1 尚未开始
- 实施分支：`codex/qt-desktop-shell`
- 代码/图谱基线：`dc4d0dd8caa07f7fd7449dc6de59678a8d274a3e`

## 1. 文档目的

本文定义 Summer GDS v2 从 `pywebview` 桌面壳迁移到
`PySide6 + QtWebEngine` 桌面壳的背景、确定方案、线程和生命周期契约、
冻结打包策略、实施顺序、验证门槛和回滚方式。

本文是本次迁移的权威实施计划。评审意见及其采用、调整和不采用理由记录在：

- [第一轮评审意见处置](../reviews/qt-desktop-shell-round1-disposition.md)
- [第二轮评审意见处置](../reviews/qt-desktop-shell-round2-disposition.md)

如果实施中必须改变以下任一边界，应先修改本文并重新评审：

- 是否继续保留 Web UI 和 Flask loopback API。
- 是否改变 YAML v2、GUI API 或几何流水线。
- 是否改变对外入口 `summer-gds-gui`。
- 是否增加用户端运行时、安装前配置或用户可见启动参数。
- 是否改变文件对话框响应语义、超时或 shutdown 顺序。
- 是否把 Windows ARM 上的 x64 emulation 证据当作原生 Windows x64
  发布证据。

## 2. 背景、证据和边界

### 2.1 当前 v2 结构

当前 GUI 由以下部分组成：

- `src/summer_gds/gui/templates/index.html`：本地页面骨架。
- `src/summer_gds/gui/static/app.js`：配置构建器和前端状态。
- `src/summer_gds/gui/static/style.css`：本地样式。
- `src/summer_gds/gui/server.py`：Flask 页面和 GUI API。
- `src/summer_gds/gui/service.py`：YAML、预览、文件选择和 GDS 导出的
  GUI 服务边界。
- `src/summer_gds/gui/launcher.py`：启动 Flask 和 `pywebview`。
- `src/summer_gds/gui/desktop.py`：`pywebview` 文件对话框适配器。

业务核心与前端通过 YAML v2 和本地 HTTP API 交互。Web UI 不依赖
CDN、Node.js、React、Vue 或其他浏览器框架。

### 2.2 已观察到的问题

当前 Windows 桌面壳调用链为：

```text
pywebview
  -> WinForms backend
  -> pythonnet / clr-loader
  -> Microsoft .NET Desktop Runtime
  -> WebView2 renderer
```

部分 Windows 11 目标机可以运行，另一些目标机在
`pythonnet/clr` 导入或桌面后端初始化时失败。当前
`SummerGDS.spec` 已记录该问题。

这与“安装或解压后直接双击使用”的产品目标冲突。用户不应理解或手工安装
Python、.NET Desktop Runtime、WebView backend 或开发工具。

### 2.3 旧版正向证据的有效范围

`summer_gds_v1/web_gui/` 曾使用：

```text
PySide6 QWebEngineView
  -> Flask
  -> Summer GDS Python code
```

旧版在目标使用环境中通过过实际运行，说明 QtWebEngine 承载本地 Web UI
在本项目中不是全新路径。

该证据不能外推为：

- 当前 v2 文件对话框线程桥已经验证；v1 保存流程使用
  `QWebEngineProfile.downloadRequested`，不是当前设计。
- 当前 PyInstaller spec 已能完整冻结 PySide6/QtWebEngine。
- 当前 KLayout、PySide6 和 Python 版本组合已在所有目标平台验证。

本迁移只复用桌面壳模式，不恢复旧页面、旧 API、旧数据协议或 linkage 系统。

### 2.4 当前可重复基线

2026-07-29 已重新验证：

- Graphify 报告基于 commit `dc4d0dd`，与当前 `HEAD` 一致。
- `uv run pytest --collect-only -q`：`84 tests collected`。
- `uv run pytest -q`：`84 passed`。
- 当前本地 Python：3.13.3。
- 当前命令环境报告为 macOS 26.5.1、`x86_64`；后续产物记录不得把
  “宿主硬件”和“当前进程架构”混写。
- 当前 lock 中 KLayout 为 0.30.8。

测试数量只记录为 pytest `collected items`，不称为“测试函数数”。新增
parameterization 后不把固定数字长期写成质量目标。

## 3. 目标与非目标

### 3.1 用户目标

- 用户获得一个安装包或应用包。
- 安装后只有一个 Summer GDS 入口和一个应用生命周期。
- 双击后直接显示 GUI。
- 不要求安装 Python、.NET Desktop Runtime、Node.js 或开发工具。
- 不要求配置 renderer、环境变量或命令行参数。
- 离线环境可以完成 YAML、SVG preview 和 GDS 工作流。

“一个 App”指一个安装入口、快捷方式和生命周期，不要求安装目录物理上
只有一个 EXE。QtWebEngine、KLayout 和 matplotlib 包含原生库和资源，
首选可靠的 onedir 目录，再由安装器隐藏内部结构。

### 3.2 工程目标

- 保留当前 Web UI、Flask GUI API、YAML v2 和几何/writer 语义。
- 保持 `summer-gds-gui` 命令不变。
- 删除生产路径上的 `pywebview/pythonnet`。
- 保持 loopback 随机端口、session token 和 path token 安全边界。
- 把 Qt 依赖限制在桌面壳和 dialog bridge。
- 明确定义并测试 dialog、启动、renderer failure 和 shutdown 状态。
- 在 macOS 本地完成 source run、自动测试、真实窗口和 onedir smoke。
- 把 Windows ARM x64 emulation 与原生 Windows x64 发布门严格分开。

### 3.3 非目标

本迁移不包含：

- 重做视觉设计或前端业务交互。
- 把 vanilla JavaScript 改成 React/Vue，或引入 npm 构建链。
- 修改 YAML v2、geometry、GDS writer 或 CLI 契约。
- 把 Flask 改成 QWebChannel、FastAPI 或 sidecar protocol。
- 增加 `--headless` 等用户可见启动模式。
- 自动更新。
- 当前阶段完成正式签名、notarization、安装器品牌设计或多架构发布。
- 长期维护两套可选桌面壳。
- 依赖同步 Flask/Werkzeug 的非稳定客户端断连信号来保证 dialog 正确性。

## 4. 方案选择

### 4.1 候选方案

| 方案 | 现有代码复用 | 用户端依赖控制 | 构建复杂度 | 结论 |
| --- | --- | --- | --- | --- |
| PySide6 QtWebEngine + Flask | 高 | Qt/Chromium 随包；安装器处理实际 runtime | 中 | 采用 |
| Electron + Python sidecar | 高 | Chromium 随包 | 高；两套 runtime 和进程协议 | 强备选 |
| Tauri + Python sidecar | 高 | 仍需管理 WebView2 | 高；增加 Rust 和 sidecar | 暂不采用 |
| C# WebView2 + Python sidecar | 高 | 可 self-contained，但 WebView2 仍需管理 | 高；Windows 专用 | 暂不采用 |
| Flask + 系统浏览器 | 最高 | 无桌面壳 | 低 | 仅保留为开发诊断路径 |

### 4.2 采用 QtWebEngine 的理由

1. 旧版有实际运行证据。
2. Qt 与 Python 处于同一进程，不新增 sidecar 握手和父子进程回收协议。
3. QtWebEngine 随应用携带 Chromium，不走 WinForms/pythonnet。
4. 当前 Web UI 和 Flask API 可以保留。
5. 改动集中在 `src/summer_gds/gui/`、依赖和打包配置。
6. Qt 官方列明 QtWebEngine 部署所需 helper、resources、locales 和
   platform-specific 文件，可以转化为自动产物清单。

### 4.3 已接受的代价

- 应用目录和安装包显著增大。
- QtWebEngine 包含 helper process、resource、locale 和 platform plugin，
  冻结包 smoke 是硬门槛。
- Windows QtWebEngine 需要适用的 Visual C++ runtime；不能把处理责任留给
  用户，必须在 clean-machine gate 验证。
- Qt/PySide6 和第三方组件的分发许可检查必须前置。
- macOS 正式分发最终需要签名和 notarization，但不属于本轮代码改造。

### 4.4 交付形态

顺序固定为：

1. source run；
2. PyInstaller onedir；
3. 安装器封装 onedir；
4. 只有前三项稳定后才评估 onefile。

onefile 不是发布要求。QtWebEngine 运行时仍需要展开 helper 和资源，
强行单文件会增加启动、杀毒扫描和诊断成本。

## 5. 依赖和平台矩阵

### 5.1 初始锁定组合

实施阶段的首个候选组合固定为：

| 组件 | 初始版本 | 管理位置 | 说明 |
| --- | --- | --- | --- |
| Python | 3.13.x | 构建环境，记录完整 patch | 项目当前要求 `>=3.13` |
| PySide6 | `6.11.1` | runtime dependency + `uv.lock` | meta wheel 同步提供 Essentials/Addons，QtWebEngine 位于 Addons |
| PyInstaller | `6.21.0` | 独立 packaging dependency group + `uv.lock` | 不加入用户运行时依赖 |
| KLayout | `0.30.8` | 现有 `uv.lock` | 先不同时升级 KLayout，避免把壳迁移与几何依赖升级耦合 |

Phase 1 dependency probe 失败时，应记录具体 wheel/import/build 证据后修改
精确版本并重跑全部门槛，不能悄悄放宽为大版本范围。

### 5.2 wheel 交集与 Windows ARM 定位

2026-07-29 的 PyPI wheel 清单显示：

- PySide6 6.11.1：Windows AMD64 和 Windows ARM64。
- PyInstaller 6.21.0：Windows AMD64 和 Windows ARM64。
- KLayout 0.30.8：Windows AMD64/Win32，没有 Windows ARM64。
- PySide6 6.11.1 没有 Win32 wheel。

因此三者的完整 Windows 交集只有 AMD64。Parallels Windows ARM 阶段
固定为：

```text
Windows 11 ARM host
  -> Windows x64 emulation
  -> AMD64 Python 3.13
  -> AMD64 SummerGDS onedir
```

不构建 Win32，不宣称 native ARM。正式支持仍由原生 Windows 11 x64
clean-machine gate 决定。

## 6. 目标架构和运行契约

![Qt 桌面壳目标架构](../diagrams/qt-desktop-shell-target-architecture.svg)

可编辑图源：
[`qt-desktop-shell-target-architecture.mmd`](../diagrams/qt-desktop-shell-target-architecture.mmd)。

### 6.1 模块职责

目标布局：

```text
src/summer_gds/gui/
├── launcher.py        # 稳定入口、matplotlib 预热、顶层异常
├── runtime.py         # Flask loopback server handle、request gate 和 readiness
├── qt_shell.py        # QApplication、窗口、WebEngine、shutdown coordinator
├── qt_dialog.py       # Flask worker 到 Qt GUI thread 的 dialog bridge
├── bundle_probe.py    # frozen-only 私有验收协议；不导入 Qt
├── server.py          # GUI 页面/API 和 production Flask 配置
├── service.py         # GuiSession、SaveFileDialog protocol、DialogFailure
├── presenter.py       # 保留
├── templates/         # 保留
└── static/            # 仅增加内部 app-ready marker
```

依赖方向：

- `launcher.py` 是唯一桌面入口，不含业务几何逻辑。
- matplotlib 的 `Agg`/font/backend 预热继续由 `launcher.py` 负责，并在
  任何可能触发 matplotlib 的应用模块 import 之前执行。
- `runtime.py` 不导入 PySide6、pywebview 或 matplotlib。
- `qt_shell.py` 拥有 Qt 对象、页面承载和生命周期协调。
- `qt_dialog.py` 是唯一调用 `QFileDialog` 的模块。
- `bundle_probe.py` 只实现 frozen bundle 验收所需的环境校验、受限路径
  adapter、原子 marker/command 文件；不提供公共 CLI、HTTP route 或任意路径
  选择能力，也不导入 Qt。
- `server.py` 不导入 Qt。
- `service.py` 不导入 Qt；`DialogFailure` 是 framework-neutral exception。
- `app/`、`schema/`、`geometry/`、`writer/` 不导入 GUI 或 Qt。

### 6.2 启动顺序

1. `launcher.main()` 初始化日志并完成 matplotlib 预热。
2. 解析 §7.4.1 的私有 bundle probe 激活环境：未设置时完全禁用；只设置
   一部分、值非法或非 frozen 进程尝试激活时，启动失败而不回落到普通模式。
3. 创建或取得 `QApplication`。
4. 创建 session token、`GuiSession` 和 off-the-record WebEngine profile。
5. 普通模式创建 Qt dialog bridge；合法 probe 模式注入只能访问本次 probe
   root 固定文件名的 deterministic adapter。
6. `create_app()` 以 production 配置创建 Flask app。
7. `start_loopback_server()` 在 `127.0.0.1` 随机端口启动 server thread。
8. runtime 在 5 秒总时限内轮询 GET `/`；只有收到预期 HTML 才视为 ready。
9. 创建 `QMainWindow`、受限 `QWebEnginePage` 和 `QWebEngineView`。
10. `setUrl()` 加载本次 loopback origin。
11. `loadFinished(true)` 后执行一次 DOM/app-ready 检查；通过后显示 ready
    状态。

ready probe 失败、初始页面加载失败或 DOM 检查失败时，必须写 crash log、
显示 Qt 原生错误并执行同一套幂等清理。`make_server()` 同步 bind 的事实
不替代“已经能处理 HTTP 请求”的 readiness 证明。

### 6.3 文件对话框桥

Flask route 在 worker thread 运行，Qt widget 只能由 GUI thread 操作。
`GuiSession` 不得直接创建 `QFileDialog`。

![Qt 文件对话框线程桥](../diagrams/qt-desktop-shell-file-dialog.svg)

可编辑图源：
[`qt-desktop-shell-file-dialog.mmd`](../diagrams/qt-desktop-shell-file-dialog.mmd)。

#### 6.3.1 接口和错误

`SaveFileDialog` 保持：

```python
choose_open_path(kind: str) -> Path | None
choose_save_path(kind: str, suggested_name: str | None) -> Path | None
```

允许实现抛出 `DialogFailure(code, safe_message)`。`GuiSession` 捕获并映射为
现有 issue response，不把 Qt 类型带入服务层。

响应语义固定为：

| 场景 | HTTP | `ok` | `canceled` | error code |
| --- | --- | --- | --- | --- |
| 选择路径 | 200 | `true` | 不返回 | 无 |
| 用户取消 | 200 | `false` | `true` | 无 |
| 已有 dialog | 200 | `false` | `false` | `dialog_busy` |
| worker 超时 | 200 | `false` | `false` | `dialog_timeout` |
| Qt 执行异常 | 200 | `false` | `false` | `dialog_error` |
| 应用关闭 | 200（若仍能回写） | `false` | `true` | 无 |

请求格式和鉴权错误继续使用现有 400/403；dialog domain error 不改 HTTP
协议。前端必须显示 `errors`，不能把 busy/timeout/error 显示成“用户取消”。

#### 6.3.2 single-flight

- bridge 使用 single-flight：任一时刻最多一个 active request。
- 第二个请求原子地立即失败为 `dialog_busy`。
- 不排队、不等待前一个 worker、不打开第二个 modal。
- single-flight 状态锁只保护状态转换，不在显示 modal 或等待用户时持有。
- `QFileDialog` 使用可持有实例和异步 `open()`/finished signal，不使用无法
  定向关闭的静态 convenience function。

#### 6.3.3 超时和终态

- `DIALOG_WAIT_TIMEOUT_SECONDS = 100`。
- 前端现有 `FILE_DIALOG_TIMEOUT_MS = 120000` 保持不变。
- request 的终态只能从 pending 原子转为 selected、canceled、failed、
  timed_out 或 closing 之一；任何终态都不能被第二次完成覆盖。
- worker 超时后把 request 标为 `timed_out`，向 GUI thread 发 cancel，
  返回 `dialog_timeout`。
- GUI late result 必须被丢弃，不能返回路径、不能创建 path token。
- active gate 只有在 GUI thread 完成或关闭原 dialog 后才释放；worker
  超时本身不能允许第二个 modal 与旧 modal 并存。
- Qt 异常经过结果通道返回脱敏 `dialog_error`；不得伪装成取消。
- 同步 Flask/Werkzeug 的客户端断连检测不是 correctness 依赖。若未来有
  可靠信号，可以提前触发同一 cancel 状态机，但不能形成另一套语义。

### 6.4 `GuiSession` 线程安全

当前 `path_tokens` 是 Flask worker 共享的唯一显式可变容器。策略固定为：

- 新增一个普通 `threading.Lock`；不使用 `RLock`，因为锁内 helper 不回调
  公共方法。
- dialog 在锁外执行。
- `choose_save_path()` 在进入 dialog 前加锁清理过期 token；成功选择后再次
  加锁清理并插入 token。
- `_resolve_path_token()` 在锁内执行查找、过期删除和 kind 校验。
- `close()` 在锁内清空 token，再清理 session 目录。
- token 在 TTL 内保持可复用，支持“目标存在 -> 用户确认 -> force 重试”；
  不改成单次消费。
- preview 使用前端单调递增 request ID 生成不同临时文件；增加并发 preview
  测试，确保不同 ID 不互相删除。
- shutdown 必须先阻止新 API/取消 dialog，再在 server 请求已收敛后调用
  `session.close()`，避免清理目录与在途 preview/export 竞争。

### 6.5 shutdown

![Qt 桌面壳退出顺序](../diagrams/qt-desktop-shell-shutdown.svg)

可编辑图源：
[`qt-desktop-shell-shutdown.mmd`](../diagrams/qt-desktop-shell-shutdown.mmd)。

关闭序列只能由 `qt_shell.py` 的幂等 coordinator 执行：

1. 原子地从 `running` 进入 `closing`，同时记录一个
   `time.monotonic() + 10s` 的唯一 deadline，并在 GUI thread 启动对应的
   single-shot hard-deadline timer；重复 close 不启动第二条序列。
2. window 拒绝本次 close event 并禁用/隐藏交互，保持 Qt event loop 可运行。
3. bridge 立即拒绝新 dialog，关闭 active `QFileDialog`，唤醒 pending worker。
4. 调用 `RequestGate.begin_shutdown()`；此后的新 API 返回 503，已经进入的
   API 保持计数并开始收敛。
5. daemon 非 GUI shutdown thread 调用 server `shutdown()`，再以同一个
   deadline 的 remaining time 有界 join daemon serve thread；GUI thread
   不等待网络线程。daemon 只用于 hard-timeout 后进程能退出，正常路径仍必须
   join。
6. 同一 shutdown thread 调用
   `RequestGate.wait_drained(max(0, deadline - time.monotonic()))`；无论
   join/drain 成败，
   都在 finally 路径 best-effort 且仅一次调用 `server_close()`。
7. 只有 serve thread 已停止、request gate 已排空，且 hard-deadline timer
   尚未先把 coordinator 置为 `timed_out` 时，才显式且仅一次调用
   `session.close()`；任一条件超时都不得与 worker 并发删除 session 目录，
   而是保留目录并记录 deferred stale cleanup。worker 完成前必须再次 CAS
   coordinator 终态，不能在 watchdog 胜出后晚到清理。
8. queued completion 回到 GUI thread；正常 worker completion 取消 watchdog。
   若 watchdog 先触发，则它使用同一个 completion 路径标记失败、保留 session
   并请求非零退出。两条路径都销毁 page/profile/window，最后调用
   `QApplication.exit(code)`；probe 模式只有在 ready marker 已发布后，才在
   exit 前写入 §7.4.1 的 complete marker。
9. `aboutToQuit` 只调用同一 coordinator 作为兜底，不实现第二套清理。

`runtime.py` 提供 framework-neutral `RequestGate`，`server.py` 用
`before_request`/`teardown_request` 接入：

- session-token 鉴权通过后，API request 调用 gate 的原子 `try_enter()`；
  只有成功进入才增加 in-flight count，并在 `flask.g` 保存 request-local
  entered flag。
- `teardown_request` 先原子清除该 flag，再且仅再调用一次 `leave()`，即使
  route 抛异常也成立；403、closing 503、页面 `/` 和其他未成功 enter 的请求
  永远不调用 `leave()`。
- `leave()` 减少计数并通知 condition；计数下溢是 assertion/test failure，
  不能静默截断为零。
- `begin_shutdown()` 原子切到 closing；之后的新 API 返回 HTTP 503 和
  `app_closing` issue，不进入 `GuiSession`。
- `wait_drained(timeout)` 只等待已经进入的请求；dialog worker 会先被 bridge
  cancel 唤醒。
- 页面 `/` 不是 shutdown 正确性的入口；server shutdown 负责停止新的连接。

`QApplication.setQuitOnLastWindowClosed(False)`，确保关闭最后一个窗口不会绕过
coordinator。`aboutToQuit` 只连接 bridge 的无阻塞 cancel/reject 兜底和日志；
正常清理不依赖此时再启动异步工作。

默认 shutdown 总时限为 10 秒，server join 和 request drain 共用这一 deadline，
不能分别各等 10 秒。若 serve thread 或在途非 dialog worker 未在时限内收敛，
记录 warning，不与 worker 并发删除 session 目录；保留临时目录供下次启动的
stale-session cleanup 回收，然后由 GUI watchdog 结束进程。正常关闭必须以
0 退出且无残留端口、server thread 和 session 目录；timeout/cleanup failure
必须非零退出。

### 6.6 WebEngine 安全和故障策略

profile 和网络：

- 使用 `QWebEngineProfile(parent)` 无 storage name 的独立
  off-the-record profile。
- 不创建持久 cookie/cache/profile 目录。
- 只允许本次 `http://127.0.0.1:<random-port>` origin。
- 主 frame 外部导航、新窗口、download 和外部 subresource 均拒绝。
- 默认拒绝 camera、microphone、geolocation、notification 等页面权限。
- 不启用 DevTools 或 remote debugging。
- 不使用 WebEngine download 处理 YAML/GDS。
- 保留 session token header、path token、随机端口和 loopback host。
- 静态资源测试解析 HTML/CSS/JS 引用；允许相对资源和本次 loopback，
  禁止公网依赖。不能用简单搜索 `http://` 误伤 loopback 设计。

可观测性：

- 自定义 `QWebEnginePage.javaScriptConsoleMessage()`：warning/error 转发到
  Python log，info 只在开发 debug 级别记录；单条截断并脱敏。
- `app.js` 初始化完成后设置 `window.SUMMER_GDS_APP_READY = true`。
- `loadFinished(true)` 后用 `runJavaScript` 检查 `#app`、`#workspace` 和
  app-ready marker。
- 初始 `loadFinished(false)` 或 DOM 检查失败显示原生致命错误并退出。
- 监听 `renderProcessTerminated(status, exit_code)`。
- shutdown 期间的正常 renderer 退出忽略；运行期间的 abnormal/crashed/
  killed 状态写日志、取消 pending dialog、显示原生错误并退出。
- 首版不自动 reload。自动 reload 可能无提示丢失未保存的浏览器状态并形成
  crash loop，必须等有状态恢复设计后另案评审。
- 首版不引入 QWebChannel heartbeat。

### 6.7 Flask production 配置

- `create_app()` 显式设置 `DEBUG=False`、`TESTING=False`。
- 生产启动不用 `app.run()`，不用 reloader，不套 Werkzeug debugger/
  `DebuggedApplication`。
- 打包测试断言这些配置和 server 创建路径。
- 现有 `SUMMER_GDS_CLOSE_ON_TEARDOWN` teardown 不是应用生命周期入口；
  Qt coordinator 显式关闭 session。

## 7. 冻结打包设计

### 7.1 权威配置

- 仓库根、tracked 的 `SummerGDS.spec` 是唯一权威 spec。
- `tests/SummerGDS.spec` 是本地已有 untracked 文件；本迁移不删除、不修改、
  不提交它。
- PyInstaller 构建必须在目标 OS 上执行，不做 macOS 到 Windows 交叉构建。
- 首个目标始终是 windowed onedir。

### 7.2 PySide6/QtWebEngine 收集策略

`qt_shell.py` 必须直接 import 实际使用模块：

```text
PySide6.QtCore
PySide6.QtGui
PySide6.QtWidgets
PySide6.QtWebEngineCore
PySide6.QtWebEngineWidgets
```

spec 策略：

1. 使用锁定的 PyInstaller 6.21.0 内置 PySide6 hooks 作为默认收集机制。
2. 不默认调用 `collect_all("PySide6")`，不收集未使用的 Qt 模块/QML/plugin。
3. 仅当产物清单证明内置 hook 漏项时，给根 spec 增加最小、带注释的
   `datas`/`binaries`/`hiddenimports`；每个补项必须对应一个失败证据和自动
   断言。
4. `collect_all("PySide6")` 只允许作为临时诊断实验，不进入发布 spec。
5. 构建日志记录 Python、PySide6、Qt、PyInstaller、KLayout、OS 和进程架构。

每个平台的产物检查至少找到：

| 类别 | macOS | Windows AMD64 |
| --- | --- | --- |
| platform plugin | `libqcocoa.dylib` | `qwindows.dll` |
| WebEngine helper | app 的 `Helpers/.../QtWebEngineProcess.app` | `QtWebEngineProcess.exe` |
| Chromium resources | `icudtl.dat`、`qtwebengine_resources*.pak` | 同左 |
| locales | 至少构建所带 `qtwebengine_locales` 且能加载 `en-US`/`zh-CN` | 同左 |
| Qt libraries/frameworks | 由锁定 hooks 收集并可被 helper 解析 | 同左 |

路径以 PyInstaller 实际布局为准，不通过设置用户环境变量修复错误 bundle。
Qt 官方部署文档要求的 helper/resources/locales 是清单来源。

### 7.3 KLayout 最小收集和原生依赖

当前生产源码只 `import pya`。本机 import trace 需要：

```text
pya
klayout.db
klayout.dbcore
klayout.pya
klayout.pyacore
klayout.tl
klayout.tlcore
```

实施动作：

- 删除 `collect_submodules("klayout")`。
- 删除当前 spec 中未实际触发的 `klayout.lay`、`rdb`、`lib`、`pex` 等
  hiddenimports。
- 先用 PyInstaller 分析结果和一次最小构建确定真正需要的 KLayout
  extension/data/plugin；不盲目 `collect_dynamic_libs("klayout")`。
- 用 GDS 生成和读取 smoke 证明 GDS plugin 仍完整。
- macOS 用 `otool -L`、Windows 用 `dumpbin /dependents` 或等价工具记录
  KLayout 与 QtWebEngine 二进制依赖。
- 产物不得出现由 KLayout 额外带入的另一套 Qt。当前源码审计没有证明存在
  冲突，因此风险状态是“需逐平台排除”，不是“已确认冲突”。

### 7.4 自动 bundle gate

新增 `scripts/verify_desktop_bundle.py` 或等价脚本，输入明确的 bundle root，
不依赖默认 `dist/` 猜测。它必须：

1. 读取 PyInstaller Analysis/TOC/warning，失败于 missing required module。
2. 断言所需 Qt platform plugin、WebEngine helper、resources 和 locales
   存在且 helper 可执行。
3. 断言产物模块/TOC 不含 `webview`、`pythonnet`、`clr_loader`、`clr`。
4. 对 `index.html`、`app.js`、`style.css`、favicon 做 SHA-256，断言与源码
   一致。
5. 解析动态库依赖，断言没有引用项目 `.venv`、源码目录或构建机上的
   非系统绝对库路径。
6. 生成 Qt6Core、Qt6Gui、Qt6Widgets、Qt6Network、
   Qt6WebEngineCore/Widgets 的 normalized dependency inventory。每条边记录
   loader 声明、解析后的 bundle-relative path、canonical realpath、SHA-256，
   以及 macOS Mach-O install name/framework root 或 Windows PE 实际 DLL
   来源。symlink/helper 对同一 canonical entity 的引用允许；同一逻辑库解析到
   两个独立 canonical 文件或 bundle root 时失败，即使两个文件 hash 相同；
   若 KLayout extension 存在 Qt 依赖，则必须解析到与 PySide6 相同的
   canonical Qt 来源；完全不依赖 Qt 是合法结果。macOS 按每个 binary 的
   `LC_RPATH` 展开 `@rpath`/`@loader_path`/`@executable_path`；
   Windows 对 import name 做大小写不敏感的精确解析并记录最终 DLL，Qt DLL
   若只能通过 bundle 外 search path 找到则直接失败。
7. 把完整 bundle 复制到仓库外、名称含空格/中文的临时目录。
8. 清除 `PYTHONPATH`、`PYTHONHOME`、Qt/PySide/PyInstaller 开发覆盖变量，
   保留操作系统最小必要 `PATH`，从新目录启动。
9. 按 §7.4.1 创建独立 run、等待该 run 的 ready marker；不得复用旧日志、
   固定端口或只检查进程存活。
10. 通过现有鉴权 API 执行固定 YAML -> SVG -> GDS probe，再用同一
    shutdown coordinator 关闭；要求 complete marker、进程退出码、端口、
    session 临时目录和输出文件全部符合 §7.4.1。

不对全部二进制做全局 `strings | grep /Users/`，因为编译器元数据可能产生
误报；以 TOC、动态库解析、静态资源 hash、迁移目录和真实运行共同证明。

#### 7.4.1 私有 bundle probe 控制协议

![Qt 桌面壳 bundle probe 协议](../diagrams/qt-desktop-shell-bundle-probe.svg)

可编辑图源：
[`qt-desktop-shell-bundle-probe.mmd`](../diagrams/qt-desktop-shell-bundle-probe.mmd)。

这个协议只解决 frozen app 的自动验收控制，不是产品功能，也不形成第二个
用户入口。代码位于 `bundle_probe.py`；Qt `QTimer` 和 shutdown coordinator
仍由 `qt_shell.py` 持有。

**激活和失败关闭**

- verifier 为每次运行生成 256-bit 随机 `run_id`，编码为 64 位小写 hex。
- verifier 在系统临时目录下独占创建
  `summer-gds-bundle-probe-<run_id>/`。POSIX 权限为 `0700`；Windows 使用
  当前用户 `%TEMP%` 的私有 ACL，并拒绝 `Everyone`/`Users` 可写目录。
- app 只读取两个成对出现的内部环境变量：
  `SUMMER_GDS_BUNDLE_PROBE_ROOT` 和 `SUMMER_GDS_BUNDLE_PROBE_RUN_ID`。
- 只有 `sys.frozen` 为真、`run_id` 格式正确、root 是系统临时目录的直接
  canonical child、目录名与 `run_id` 匹配、目录不是 symlink/reparse point
  且权限/owner 校验通过时才激活。
- 两个变量都不存在时，probe 代码完全休眠；只设置一个、值非法或 source
  进程尝试激活时，app 写脱敏错误并非零退出，不得静默回落到普通 GUI。
- 激活后立即启动 `PROBE_TOTAL_TIMEOUT_SECONDS = 180` 的 GUI-thread
  single-shot timer；verifier 等待 ready 的上限
  `PROBE_READY_TIMEOUT_SECONDS = 60`。总 timer 到期而仍未消费合法 shutdown
  command 时，必须以 `probe_command_timeout` 调用同一 coordinator。
- 安装器、spec、产品快捷方式、用户文档和正常 test fixture 永远不设置这两个
  变量；不增加 public CLI flag、HTTP quit route 或 remote-debugging port。

**文件和 schema**

verifier 创建 root 时先断言它为空，再写入固定 fixture。双方只使用以下固定
文件名，所有读写都在 canonical root 内完成，并拒绝绝对路径、`..`、symlink
和 reparse escape：

- `input.yaml`
- `output.yaml`
- `output.gds`
- `session-root/`（只允许 `GuiSession` 在其下创建本次运行目录）
- `ready-<run_id>.json`
- `command-<run_id>.json`
- `complete-<run_id>.json`

JSON 统一使用 UTF-8、`schema_version: 1` 和完全匹配的 `run_id`。写方先在
同目录创建 owner-only 临时文件，flush/fsync 后以 atomic replace 发布；读方
只接受普通文件、限制大小为 16 KiB，并在解析后再次核对 canonical parent。
marker/command 的最小 schema 固定为：

```json
{
  "schema_version": 1,
  "run_id": "<64-lower-hex>",
  "pid": 1234,
  "origin": "http://127.0.0.1:49152",
  "frozen": true,
  "process_arch": "x86_64",
  "dom_ready": true
}
```

```json
{
  "schema_version": 1,
  "run_id": "<64-lower-hex>",
  "command": "shutdown"
}
```

```json
{
  "schema_version": 1,
  "run_id": "<64-lower-hex>",
  "pid": 1234,
  "result": "ok",
  "cleanup": {
    "server_stopped": true,
    "request_gate_drained": true,
    "server_closed": true,
    "session_removed": true
  }
}
```

complete marker 描述的只是 app shutdown/cleanup，不代表 verifier 的
YAML/SVG/GDS 业务断言已通过。`result` 只能是 `ok` 或 `failed`；`ok` 当且仅当
合法 shutdown command 已被接受、coordinator 正常完成且四个 cleanup 字段
均为 true。`failed` 还必须带 `error_stage`，值只能是
`invalid_probe_command`、`probe_command_timeout`、`server_join_timeout`、
`request_drain_timeout`、`server_close_failed` 或
`session_cleanup_failed`。启动或 DOM ready/ready marker 发布前失败时不会有
complete marker，verifier 以非零退出和 crash log 判失败。同时出现多个失败时
按上述枚举顺序记录第一个，完整细节只进入脱敏日志。

ready marker 只在 WebEngine `loadFinished(true)`、DOM selector 和
`window.SUMMER_GDS_APP_READY` 全部通过后写入。它不包含 session token 或
path token。verifier 从本次 marker 的 origin GET `/`，从现有 HTML bootstrap
提取 session token，再只使用现有 `X-Summer-GDS-Token` 鉴权；不绕过
`server.py` 的真实安全边界。origin 必须精确解析为无 userinfo/path/query/
fragment 的 `http://127.0.0.1:<1-65535>`；verifier 使用禁用 proxy、禁止
redirect 的直连 client，并拒绝 hostname、IPv6 alias 或重定向后的等价地址。

**业务 probe 和受控 dialog**

1. verifier 在启动前把固定 fixture 原子写为 `input.yaml`。
2. probe 模式注入 framework-neutral deterministic dialog adapter：
   open YAML 只能返回 `input.yaml`，save YAML 只能返回 `output.yaml`，
   save GDS 只能返回 `output.gds`；其他 kind、suggested path 或逃逸路径
   立即失败。
   `GuiSession` 的 temp root 同时固定为 `session-root/`，使 verifier 能在
   不暴露 session path/token 的前提下独立判断本次 session 是否清理。
3. verifier 在一个保留原始异常的 `try/finally` 中依次调用
   `/api/yaml/open`、`/api/parse`、`/api/validate` 和 `/api/preview/svg`，
   校验响应、SVG 内容和 request ID。
4. 同一 `try` 中通过两次 `/api/file/choose-save` 取得服务层生成的 path
   token，再调用 `/api/yaml/save` 和 `/api/export/gds`；校验 YAML、非空
   GDS，并用 KLayout read-back 检查预期 top cell。
5. 无论第 3/4 步成功、断言失败还是 HTTP 超时，`finally` 都原子发布一次合法
   matching shutdown command；cleanup 的成功不能覆盖或改写原业务失败。
6. deterministic adapter 只用于该自动 probe。真实 `QFileDialog` 的
   modal、前置、cancel 和 Unicode 路径仍由 source/bundle 的人工真实窗口
   smoke 验收，自动 probe 不冒充这项证据。

**关闭、结果和清理**

- shell 的低频 `QTimer` 在 GUI thread 读取并消费一次 command；唯一允许的
  command 是 `shutdown`。合法 command 被消费后先取消 180 秒 probe timer，
  再调用 §6.5 的同一个 coordinator；不发送 `SIGTERM`，也不创建隐藏 HTTP
  控制面。
- matching 文件若超过大小、schema/run ID 不匹配、不是普通文件或 command
  非法，取消 probe timer 后按 `invalid_probe_command` 触发同一 coordinator
  并非零退出；不得忽略后继续等待另一个命令。
- 若 ready marker 已发布，coordinator 在清理后、
  `QApplication.exit(code)` 前写 complete marker；ready 前失败不写。
  清理失败时写 `result: "failed"` 和安全的阶段码；不得谎报 `ok`。
- 成功 gate 要求 ready/complete 的 `run_id`、PID 和本次子进程一致，进程在
  195 秒 hard ceiling 前以 0 退出，complete 为 `ok` 且四个 cleanup 字段均为
  true，origin 端口已关闭，`session-root/` 下没有本次 session 目录残留；
  业务 probe 断言还必须独立全部通过。
- verifier 的进程 hard-kill ceiling 为启动后 195 秒，即 app 180 秒总 deadline、
  coordinator 10 秒 deadline 和 5 秒退出余量之和。只有超过此上限且子进程仍
  存活时，verifier 才可终止整个进程树；该结果固定为失败，不得计作 graceful
  shutdown，也不得覆盖最初的业务或 ready 失败。
- 唯一 root + 随机 `run_id` 使旧 marker/全局日志不能满足本次运行。成功时
  verifier 删除 probe root；失败时保留 root、构建日志和 bundle inventory，
  并输出绝对证据路径。

### 7.5 许可证门

Phase 1 建立、发布前完成：

- 所选 PySide6/Qt 模块和第三方组件的 license inventory。
- `LICENSES/`、`THIRD_PARTY_NOTICES` 和用户可访问位置。
- 按所选许可证与分发方式适用的库替换/重链接、源码获取和 notice 检查表。
- 对 QtWebEngine/Chromium notices 的收集验证。
- 由项目负责人确认采用 commercial 许可，或确认能够遵守适用开源许可。

本文只定义工程 gate，不替代法律意见。

## 8. 详细实施计划

### Phase 0：计划、图谱和评审

交付：

- 本迁移计划及 Mermaid/SVG 图。
- 两份第一轮评审和综合处置文档。
- 两份第二轮独立评审和综合处置文档。

验收：

- reviewer 读取计划、处置文档、Graphify 图谱和实际代码。
- reviewer 只写独立 review 文档，不修改计划或代码。
- DS4P 第二轮裁决为 `APPROVE`。
- GLM 第二轮唯一 blocker R1 已按
  [第二轮评审意见处置](../reviews/qt-desktop-shell-round2-disposition.md)
  回填到 v1.3。
- 综合核对发现的依赖落点、自动 bundle 控制协议和 shutdown drain 调用缺口
  也已写成唯一实施契约；没有未处置 blocker，才进入 Phase 1。

### Phase 1：锁定基线、依赖和合规输入

动作：

- 再运行 `pytest --collect-only` 和完整 pytest，记录 collected items/pass。
- 校验 Graphify report commit、当前 `HEAD` 和工作树差异；实现前图谱使用
  `dc4d0dd` 代码基线。
- 记录 source GUI 启动、关闭、debug/crash log 和冷启动/稳定内存基线。
- 确认根 `SummerGDS.spec` 唯一权威，保护 untracked
  `tests/SummerGDS.spec`。
- 在隔离环境探测 Python 3.13.x、PySide6 6.11.1、PyInstaller 6.21.0、
  KLayout 0.30.8 的 import 和最小 WebEngine window。
- probe 通过后，把 `PySide6==6.11.1` 加入 runtime dependencies，
  `pyinstaller==6.21.0` 加入 packaging dependency group，并让
  `uv.lock` 精确记录版本；保留 pywebview 到 Phase 5，使旧壳基线在
  Phase 1-4 仍可运行，但不增加双壳用户入口。
- 用更新后的 frozen lock 再运行完整 pytest 和当前 pywebview source GUI
  smoke，证明依赖共存没有改变当前入口。
- 起草许可证 inventory/checklist。

验收：

- 现有测试全绿，口径明确。
- PySide6 Widgets/WebEngine import 在 macOS 成功。
- 初始版本组合与平台 wheel 证据记录完成；`uv.lock` 精确包含 PySide6 和
  PyInstaller，pywebview 仍暂时存在。
- 更新依赖后的 pytest 和旧壳 source smoke 仍通过。
- baseline 没有误纳 `.graphify/` 或用户 untracked 文件。

### Phase 2：提取无框架 runtime

动作：

- 将 `LoopbackServerHandle` 和 `start_loopback_server()` 移到 `runtime.py`。
- 增加 5 秒有界 HTTP readiness probe 和 stop 幂等保护。
- 在 `runtime.py` 实现 framework-neutral `RequestGate`。
- 新增 `tests/gui/test_runtime.py`，把
  `test_loopback_server_serves_gui_and_stops` 及 `urlopen` 相关 import 从
  `test_launcher.py` 移入，并在该文件增加 runtime/RequestGate 单元测试。
- 本阶段保留 `FakeWebviewModule`、`FakeWindow`、
  `test_launch_desktop_forces_edgechromium_on_windows` 和全部
  `test_pywebview_*`；pywebview 仍是当前生产壳，不能提前把它们改为 Qt fakes。
- 只在 runtime `stop()` 形状改变时同步调整 `FakeServerHandle`。
- matplotlib 预热留在 `launcher.py` 顶部，不移入 runtime。

验收：

- `runtime.py` 不导入 PySide6、pywebview 或 matplotlib。
- server start/ready/HTTP/stop/重复 stop/ready timeout 测试通过。
- `test_request_gate_rejects_new_entries_after_begin_shutdown`、
  `test_request_gate_waits_for_inflight_requests` 和
  `test_request_gate_leave_wakes_waiter` 通过。
- 旧 pywebview launcher/dialog 测试和新 runtime 测试同时收集并通过。
- stop 后端口不再接受连接。

### Phase 3：实现 dialog bridge 和 session lock

动作：

- 新增 `DialogFailure` 和确定的 response mapping。
- 给 `GuiSession.path_tokens` 增加普通 Lock 和实际 purge 调用。
- 新增 `qt_dialog.py`，实现 single-flight、异步 `QFileDialog`、100 秒
  timeout、late-result discard、exception marshalling 和 shutdown cancel。
- 更新前端 busy/timeout/error 文案，保持 120 秒 fetch timeout。

自动测试：

- `test_second_dialog_returns_busy_without_queueing`
- `test_dialog_timeout_precedes_frontend_timeout`
- `test_late_selection_after_timeout_is_discarded`
- `test_dialog_exception_maps_to_dialog_error`
- `test_shutdown_wakes_pending_dialog`
- `test_only_one_modal_exists`
- `test_path_tokens_are_locked_and_purged`
- `test_force_retry_can_reuse_valid_token`
- `test_concurrent_preview_with_distinct_request_ids_does_not_clobber`
- 中文、emoji、空格路径 open/save/cancel

preview 并发测试必须使用 barrier/fake renderer 强制两个请求重叠，不能依赖
真实渲染速度碰巧形成并发。

bridge 测试使用 fake dialog factory 和 Qt event dispatch，不实例化
`QWebEngineView`，也不弹真实 modal。创建 `QApplication` 的单元测试固定放在
`tests/gui/qt_unit/`；该目录的 `conftest.py` 在 test module collection 前先
断言 `PySide6` 尚未进入 `sys.modules`，再设置
`QT_QPA_PLATFORM=offscreen`。普通 pytest fixture 执行太晚，不允许承担这项
初始化。该子树外的测试不得依赖这个变量；变量不得写入产品环境、spec、
bundle verifier 或真实 WebEngine smoke。

### Phase 4：实现 Qt shell 和确定生命周期

动作：

- 新增 `qt_shell.py`，提供供 `launcher.py` 在 Phase 5 委托的单一
  `run_qt_shell()` 边界。
- 创建 QApplication、off-the-record profile、受限 page、view 和 window。
- 加载 ready 后的 loopback URL。
- 实现导航、subresource、权限、新窗口和 download 限制。
- 实现 JS console 转发、load/DOM check、renderer termination 和原生错误。
- 将 `RequestGate` 接入 `server.py` 的 request enter/leave 和 closing 503
  响应。
- 实现 §6.5 唯一 shutdown coordinator。
- 新增 `bundle_probe.py`，实现 §7.4.1 的 frozen-only 激活校验、固定路径
  adapter 和原子 JSON 文件；在 `qt_shell.py` 用 GUI-thread `QTimer` 把
  matching shutdown command 委托给同一 coordinator。
- `session.close()` 显式执行，不依赖 `server.py` teardown。

验收：

- `tests/gui/test_qt_shell.py` 的纯 lifecycle 测试使用 fake
  page/profile/runtime，不创建 `QApplication` 或 WebEngine；确需
  `QApplication` 的集成单测归入 `tests/gui/qt_unit/`，且仍不创建
  `QWebEngineView`。
- 通过开发者测试命令直接调用 `run_qt_shell()` 的 source real-window smoke
  显示当前 v2 页面；此命令不安装为 entry point，也不成为公共 CLI。
- 本阶段 `summer-gds-gui` 仍指向 pywebview，直到 Phase 5 连同 launcher
  测试原子切换；不增加双壳选择参数。
- load failure、DOM failure、renderer failure 的 handler 可通过 fake page/
  signal 参数测试。
- `test_api_returns_503_app_closing_after_gate_shutdown` 和
  `test_shutdown_waits_only_for_already_inflight_requests` 通过。
- `test_rejected_request_does_not_decrement_inflight` 和
  `test_request_leaves_gate_exactly_once` 通过。
- `test_shutdown_does_not_close_session_before_gate_drains`、
  `test_gate_timeout_preserves_session_directory` 和
  `test_server_close_runs_once_on_timeout` 通过。
- `test_shutdown_watchdog_rejects_late_worker_cleanup` 证明 hard deadline
  胜出后，晚到 worker 不能再调用 `session.close()`。
- `test_probe_is_dormant_without_env`、
  `test_probe_rejects_partial_invalid_or_nonfrozen_activation`、
  `test_probe_paths_cannot_escape_root` 和
  `test_probe_shutdown_command_uses_coordinator` 通过。
- `test_probe_command_timeout_invokes_coordinator` 通过。
- 正常关闭清理 server、端口和 session；重复 close 幂等。

### Phase 5：切换入口和依赖

动作：

- 保持 `summer-gds-gui = summer_gds.gui.launcher:main`。
- 确认 Phase 1 已锁定的 `PySide6==6.11.1`、`pyinstaller==6.21.0`
  和 import probe 仍通过；本阶段不改变已评审的版本组合。
- `launcher.py` 切换为 Qt shell。
- 在同一阶段从 `tests/gui/test_launcher.py` 删除
  `PyWebviewSaveFileDialog` import、`FakeWebviewModule`、`FakeWindow`、
  edgechromium 测试和全部 `test_pywebview_*`。
- 以 `test_launcher_delegates_to_qt_shell`、
  `test_launcher_propagates_qt_exit_code`、
  `test_launcher_reports_qt_shell_failure` 和干净子进程 import-boundary
  测试替换；launcher 必须原样返回 Qt exit code，测试使用 fake shell runner，
  不实例化真实 `QWebEngineView`。
- Qt dialog 的选择、取消、异常、超时和 shutdown 测试只保留在
  `tests/gui/qt_unit/test_qt_dialog.py`，不在 launcher 测试重复。
- 删除 `desktop.py`、生产 dependency `pywebview` 和生产路径 pywebview
  import。
- 不增加双壳 CLI 参数。

自动验收：

- 干净子进程导入/运行 GUI 入口时阻断 `webview`、`pythonnet`、`clr_loader`
  仍能到达 Qt 启动边界。
- 另一干净子进程导入 `summer_gds.cli`，断言未加载任何 `PySide6` 模块。
- `tests/gui/test_launcher.py` 不再引用 `summer_gds.gui.desktop`、`webview`
  或 pywebview 专属 fake；`tests/gui/test_runtime.py` 继续独立通过。
- 删除 `desktop.py` 后，pytest collect 和完整 suite 仍通过。
- `uv lock --check`/等价 frozen lock 检查通过。
- 全量 pytest 和新增 Qt 专项全绿。

### Phase 6：macOS source-run 验证

自动：

- `uv sync --frozen`（含 packaging group 时使用明确 group）。
- `uv run pytest -q`。
- runtime、bridge、session lock、shell lifecycle、静态资源本地性测试。
- production Flask 配置测试。

真实窗口：

1. 启动 `uv run summer-gds-gui`。
2. 确认 app-ready、console 和日志。
3. 创建 base、via、rings 并触发 SVG preview。
4. 保存 YAML，再重新打开。
5. 导出 GDS。
6. 分别取消一次 open/save。
7. 使用含中文、emoji 和空格的目录。
8. 关闭窗口。
9. 检查无残留 server/thread/session。

记录 source 冷启动时间、ready 后稳定内存，仅作趋势基线，不在本轮设任意
硬性能阈值。

### Phase 7：macOS onedir bundle smoke

动作：

- 按 §7 修改根 `SummerGDS.spec`。
- 构建 windowed onedir。
- 运行 `verify_desktop_bundle.py`。
- 从迁移后的仓库外 Unicode/空格目录启动产物。
- 使用 §7.4.1 的唯一 root/run ID 协议完成 app-ready、现有 API 业务 probe
  和 coordinator shutdown；不解析旧日志，不向进程发送 SIGTERM。
- 自动 probe 通过后，另行启动普通模式并执行一次真实窗口目视流程。

验收：

- Qt platform plugin、WebEngine helper/resources/locales 完整。
- KLayout 最小模块仍能生成 GDS。
- bundle TOC 不含 pywebview/pythonnet/clr。
- 静态资源 hash 与源码一致。
- 动态库不引用 `.venv` 或项目目录。
- ready/complete marker、YAML/SVG/GDS、KLayout read-back、退出码和 cleanup
  probe 通过。
- `test_bundle_verifier_publishes_shutdown_in_finally`、
  `test_bundle_verifier_rejects_redirecting_or_nonloopback_origin` 和
  `test_bundle_verifier_hard_kill_is_failure` 通过。
- 普通模式的真实 `QFileDialog` 前置、cancel 和 Unicode 路径目视通过。
- 记录 bundle 大小、冷启动和稳定内存。
- pytest 与 `document-diagrams` freshness check 同时通过。

此阶段不要求 macOS 签名或 notarization。

### Phase 8：Windows ARM 上的 AMD64/x64 emulation 验证

前提：

- 用户提供 SSH/文件传输方式和可交互登录。
- 使用 AMD64 Python 3.13 和 AMD64 wheels 构建 AMD64 onedir。
- 每次记录 OS、Python、进程、wheel 和产物架构。

自动：

- `uv sync --frozen`。
- pytest。
- Windows AMD64 onedir build。
- bundle inventory、动态依赖，以及 §7.4.1 的 ready、固定
  YAML/SVG/GDS、coordinator shutdown 和 cleanup probe。
- Defender 扫描结果和退出清理记录。

用户目视：

- 主窗口、字体和 DPI。
- modal 前置和 cancel。
- 中文/emoji/空格路径。
- SVG preview 和 GDS export。
- 关闭无残留。

结论固定表述为“Windows 11 ARM 的 x64 emulation 路径通过/失败”，不得写成
native ARM 或原生 x64 已发布。

### Phase 9：原生 Windows x64 release gate

在干净的原生 Windows 11 x64 机器：

- 无 Python、无开发工具、无预装项目依赖。
- 普通用户权限、离线启动。
- 中英文和 Unicode 用户路径。
- 安装、升级、卸载。
- 完整 GUI 工作流和 shutdown。
- Defender/SmartScreen 行为。
- Visual C++ runtime 由产物或安装器正确处理。
- 动态依赖、签名和 bundle inventory 可审计。

只有本阶段通过，才可声明 Windows x64 正式兼容。

### Phase 10：安装器和发布文档

动作：

- 选择安装器技术并封装已通过的 onedir。
- 创建开始菜单/桌面/卸载入口。
- 验证 Visual C++ runtime 的内置、检测或静默部署路径。
- 完成许可证 inventory、notices 和适用合规材料。
- 更新 `README.md`、`docs/frontend/frontend-architecture.md`、
  `docs/frontend/deployment.md` 和测试策略。
- 删除 pywebview/pythonnet 用户说明。

验收：

- 用户只需运行安装器并点击应用。
- 不要求环境变量或框架配置。
- 文档、安装器和实际 bundle 一致。

## 9. 迁移门槛

![Qt 桌面壳迁移门槛](../diagrams/qt-desktop-shell-migration-gates.svg)

可编辑图源：
[`qt-desktop-shell-migration-gates.mmd`](../diagrams/qt-desktop-shell-migration-gates.mmd)。

任何阶段失败都回到对应实现或打包阶段。不得通过以下方式获得假通过：

- 要求用户安装 Python/.NET/开发框架。
- 把 source run 当作 bundle 通过。
- 把进程存活当作页面 ready。
- 把 ARM x64 emulation 当作原生 x64。
- 放宽资源、动态库或 cleanup 检查。

## 10. 测试矩阵

| 层级 | 环境 | 自动/人工 | 必须证明 |
| --- | --- | --- | --- |
| 服务/API | Flask test client | 自动 | token、parse、preview、path token、save/export、production config |
| runtime | macOS，无 Qt | 自动 | bind/ready/stop/timeout/幂等 |
| dialog state | fake dialog + Qt dispatch | 自动 | single-flight、timeout、late result、error、shutdown |
| session concurrency | Python threads | 自动 | token lock/purge/reuse、并发 preview |
| shell lifecycle | fake page/profile/runtime，无 QApplication | 自动 | startup/load failure/renderer failure/唯一 shutdown |
| Qt source smoke | macOS 真实窗口 | 自动测试 + 人工 | WebEngine ready、真实 dialog、页面和退出 |
| bundle probe protocol | frozen-only + 私有 temp root | 自动 | run 隔离、真实鉴权 API、coordinator shutdown、cleanup |
| macOS bundle | 移动后的 onedir | 自动 + 人工 | 资源、动态库、静态 hash、业务 probe、真实 dialog |
| Windows ARM compatibility | AMD64 bundle on x64 emulation | 自动 + 用户目视 | 对应 emulation 路径 |
| Windows x64 release | 干净原生 Windows 11 x64 | 自动 + 人工 | 正式兼容和安装体验 |

不可替代关系：

- mock `sys.platform == "win32"` 不能替代 Windows bundle。
- Flask API 不能替代 Qt dialog。
- offscreen lifecycle test 不能替代真实 QWebEngine。
- source run 不能替代 frozen bundle。
- bundle inventory 不能替代业务 probe。
- deterministic probe dialog 不能替代真实 `QFileDialog` 目视验收。
- Windows ARM emulation 不能替代原生 x64。

## 11. 日志、诊断和基线指标

保留用户可发现路径：

- `~/.summer-gds-debug.log`
- `~/.summer-gds-crash.log`

Windows 对应 `%USERPROFILE%`。debug log 使用 thread-safe
`RotatingFileHandler`，每个文件 1 MiB、3 个备份、UTF-8。crash log 保留
最近一次完整启动失败。

日志至少包含：

- Summer GDS 版本和 frozen/source。
- OS、CPU、Python 进程架构。
- Python、PySide6、Qt、QtWebEngine、PyInstaller（frozen metadata）和
  KLayout 版本。
- loopback host/port，不记录 session token。
- startup/ready/load/DOM check。
- JS warning/error（截断、脱敏）。
- render termination status/exit code。
- shutdown 每一阶段和超时。

不得记录：

- session token、path token。
- YAML 全文或用户文件内容。
- 未脱敏请求体。
- 非必要完整用户路径；UI 必须显示路径时不等于可以写入 debug log。

每个平台记录：

- source 和 bundle 冷启动到 app-ready 时间。
- app-ready 后稳定内存。
- onedir 和安装器大小。

这些是回归趋势，不是本轮拍脑袋设置的发布阈值。

## 12. 主要风险和缓解

| 风险 | 触发 | 影响 | 缓解/证明 |
| --- | --- | --- | --- |
| dialog 跨线程错误 | worker 访问 QWidget | crash/deadlock | queued bridge、fake/真实 dialog test |
| dialog 双完成 | timeout 后用户选择 | token 泄漏/错误响应 | 原子终态、late result discard |
| 多 modal | 并发请求或 timeout 过早释放 gate | 用户阻塞/死锁 | single-flight、GUI 关闭后才释放 |
| token 字典竞态 | threaded Flask 并发读写 | RuntimeError/过期状态错误 | 普通 Lock、purge/reuse tests |
| session 清理竞态 | shutdown 与 preview/export 并发 | 文件错误/残留 | stop gate、收敛后 close、超时则延迟 stale cleanup |
| probe 形成隐藏后门 | 自动验收控制面进入正常启动 | 非预期文件写入/退出 | frozen-only 双变量、nonce 私有 root、固定路径、无 HTTP quit |
| QtWebEngine 漏打包 | helper/resource/locale/plugin 缺失 | 白屏/静默退出 | 内置 hooks、inventory、移动后真实启动 |
| KLayout 过度收集 | `collect_submodules`/全部动态库 | 体积和原生冲突面扩大 | import trace、最小 spec、GDS smoke |
| KLayout/Qt 二进制冲突 | 产物出现第二套 Qt | 启动/运行 crash | `otool`/`dumpbin` 依赖清单；当前状态为待排除 |
| Flask debug 误启用 | 配置回归 | 本地攻击面扩大 | production config assertions |
| JS 静默失败 | bundle 静态文件错配 | 页面看似启动但不可用 | console forwarding、DOM marker、hash |
| renderer crash | Chromium helper 异常 | UI 丢失 | 原生 fatal、日志、退出；不自动 reload |
| ARM emulation 假阳性 | 将兼容层结果外推 | 过早发布 | 固定证据标签、原生 x64 独立 gate |
| 许可证遗漏 | 冻结分发 Qt/Chromium | 发布阻塞 | Phase 1 inventory、发布前合规 gate |
| 安装体积上升 | QtWebEngine + KLayout | 分发变慢 | 接受确定性优先，记录趋势后优化 |
| 双壳长期并存 | 为回滚保留入口 | 测试矩阵翻倍 | Git rollback，不提供双壳 CLI |

## 13. 回滚策略

### 13.1 实施期

- 所有改造位于 `codex/qt-desktop-shell`。
- 按 runtime、bridge、shell、entry/dependency、packaging 分段提交。
- 旧 pywebview 文件只在迁移分支早期作为 diff/回滚证据，不提供用户入口。
- 回滚用 Git commit/branch，不通过长期保留两套 runtime。

### 13.2 门槛失败

如果 Qt 无法通过 macOS source 或 onedir：

- 回滚对应 Qt 提交。
- 保留计划、失败日志和 bundle inventory。
- 重新评估 Electron sidecar，不修改业务层协议来迁就桌面壳。

如果 macOS 通过而 Windows ARM x64 emulation 失败：

- 保留业务层和 Qt 分支。
- 定位 Windows packaging/runtime。
- 不要求用户手工安装开发框架。

如果 emulation 通过而原生 x64 失败：

- 发布状态保持 blocked。
- 保留 emulation 证据，但不宣传正式 Windows 支持。

## 14. 预期文件变更

预计新增：

- `src/summer_gds/gui/runtime.py`
- `src/summer_gds/gui/qt_shell.py`
- `src/summer_gds/gui/qt_dialog.py`
- `src/summer_gds/gui/bundle_probe.py`
- `scripts/verify_desktop_bundle.py`
- `tests/gui/test_runtime.py`
- `tests/gui/qt_unit/conftest.py`
- `tests/gui/qt_unit/test_qt_dialog.py`
- `tests/gui/test_qt_shell.py`
- `tests/gui/test_bundle_probe.py`
- `tests/gui/test_import_boundaries.py`
- packaging tests
- license inventory/notices（进入发布阶段时）

预计修改：

- `src/summer_gds/gui/launcher.py`
- `src/summer_gds/gui/server.py`
- `src/summer_gds/gui/service.py`
- `src/summer_gds/gui/static/app.js`
- `pyproject.toml`
- `uv.lock`
- 根 `SummerGDS.spec`
- `tests/gui/test_launcher.py`
- GUI 架构、部署和测试文档

Phase 5 Qt 入口和测试完成原子切换时删除：

- `src/summer_gds/gui/desktop.py`
- `pywebview` dependency
- Windows `pythonnet/clr` 诊断说明

明确不修改/不纳入：

- YAML v2 schema、geometry 和 writer 语义。
- CLI 契约。
- Web UI 视觉和业务交互。
- 用户已有 untracked `tests/SummerGDS.spec`。

## 15. 完成定义

### 15.1 本轮 macOS 改造完成

- 第二轮评审没有未处置 blocker。
- Qt 是生产桌面入口，pywebview/pythonnet 不在生产依赖/产物。
- dialog、session、startup、renderer 和 shutdown 契约实现并自动测试。
- 全量 pytest 通过。
- macOS source real-window smoke 通过。
- 移动后的 macOS onedir inventory、§7.4.1 自动业务/cleanup probe 和普通
  模式真实 dialog 目视 smoke 通过。
- Graphify 已基于实现后的 commit 重建，diagram source/SVG freshness 通过。
- Windows 阶段仍以明确的 pending 状态记录。

### 15.2 Windows ARM compatibility 完成

- AMD64 bundle 在 Windows 11 ARM x64 emulation 下通过自动和用户目视验收。
- 证据记录实际架构，不声明 native ARM 或原生 x64。

### 15.3 正式 Windows 发布完成

- 原生 Windows x64 clean-machine gate 通过。
- 安装器、runtime、签名、升级和卸载通过。
- 许可证和第三方 notice 完成。
- 发布文档与实际产物一致。

原生 x64 gate 前禁止使用“已解决所有 Windows 11 兼容问题”或“支持所有
Windows 11”作为结论。

## 16. 关联资料

项目资料：

- [前端技术架构](../frontend/frontend-architecture.md)
- [前端部署与打包](../frontend/deployment.md)
- [测试策略](../quality/testing-strategy.md)
- [当前 PyInstaller spec](../../SummerGDS.spec)
- [Graphify 报告](../../.graphify/GRAPH_REPORT.md)
- [Graphify flows](../../.graphify/flows.json)
- [DS4P 第一轮评审](../reviews/qt-desktop-shell-ds4p-review.md)
- [GLM 第一轮评审](../reviews/qt-desktop-shell-glm-review.md)
- [第一轮意见处置](../reviews/qt-desktop-shell-round1-disposition.md)
- [DS4P 第二轮评审](../reviews/qt-desktop-shell-ds4p-round2-review.md)
- [GLM 第二轮评审](../reviews/qt-desktop-shell-glm-round2-review.md)
- [第二轮意见处置](../reviews/qt-desktop-shell-round2-disposition.md)

上游资料：

- [Qt for Python deployment overview](https://doc.qt.io/qtforpython-6.8/deployment/index.html)
- [Qt for Python and PyInstaller](https://doc.qt.io/qtforpython-6.10/deployment/deployment-pyinstaller.html)
- [Deploying Qt WebEngine Applications](https://doc.qt.io/qt-6/qtwebengine-deploying.html)
- [QWebEngineProfile off-the-record semantics](https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineCore/QWebEngineProfile.html)
- [Qt licensing](https://doc.qt.io/qt-6.8/licensing.html)
- [PyInstaller stable manual](https://pyinstaller.org/en/stable/)
- [PySide6 on PyPI](https://pypi.org/project/PySide6/)
- [PyInstaller on PyPI](https://pypi.org/project/pyinstaller/)
- [KLayout on PyPI](https://pypi.org/project/klayout/)
