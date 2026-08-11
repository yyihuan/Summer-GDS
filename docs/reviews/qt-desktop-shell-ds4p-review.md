# DS4P 独立评审：Qt 桌面壳迁移

评审人：DS4P（独立架构与安全评审）
评审日期：2026-07-29
评审对象：[qt-desktop-shell-migration-plan.md](../planning/qt-desktop-shell-migration-plan.md)
评审分支：`codex/qt-desktop-shell`
评审基线提交：`dc4d0dd`
图形化证明：[GRAPH_REPORT.md](../../.graphify/GRAPH_REPORT.md)、[flows.json](../../.graphify/flows.json)

## 评审方法

本评审对照迁移计划的每一项声明与以下实体证据：

- 当前 v2 GUI 源码（`launcher.py`、`desktop.py`、`server.py`、`service.py`）
- 旧版 v1 Qt 源码（`qt_launcher.py`、`qt_mainwindow.py`）
- v2 PyInstaller spec（`SummerGDS.spec`）
- v1 PyInstaller spec（`summer_gds_v1/SummerGDS.spec`）
- Graphify 图谱（1047 节点、1947 边、53 社区）
- 现有测试（`tests/gui/test_launcher.py` 等）

对每一项发现，均给出源码文件路径和行号，或 Graphify 图谱证据。

---

## 1. 总体裁决

**裁决：`APPROVE_WITH_CHANGES`**

迁移计划在以下几点上成立、证据充分：

- 问题定位精确：`pywebview → WinForms → pythonnet/clr → .NET Desktop Runtime` 链路是已确认的 Windows 兼容故障点（`SummerGDS.spec:5-7`；迁移计划 §2.2）。
- 旧版正向证据可信：v1 在同一使用环境的 PySide6 + QtWebEngine + Flask 已通过实际运行验证（迁移计划 §2.3；`summer_gds_v1/web_gui/qt_launcher.py`、`qt_mainwindow.py` 为实物证据）。
- 架构范围限制明确：只替换桌面承载层，不触碰 YAML v2 协议、几何流水线、CLI 契约（迁移计划 §4；Graphify 社区 5、6、7、14、15 独立于 desktop shell）。
- 阶段门控设计合理：从 Phase 0 到 Phase 10 逐级递进，每阶段有明确验收和回滚策略（迁移计划 §7、§8）。

但存在 4 个阻塞性问题和若干高优先级风险，必须在实施前在计划中回填或在 Phase 1–3 中消除。以下详述。

---

## 2. 阻塞性发现

### B1 — PyInstaller spec 完全缺失 PySide6/QtWebEngine 打包策略

**严重程度**：阻塞
**类别**：packaging

当前 `SummerGDS.spec`（项目根，版本 `tests/SummerGDS.spec` 一致）仅收集 klayout、matplotlib、flask 等依赖。没有任何 PySide6 相关的 `collect_data_files`、`collect_submodules`、`collect_dynamic_libs` 调用（`SummerGDS.spec:36-98`）。

Qt 平台最少需要以下资源才能运行：

- 平台插件：macOS 需要 `libqcocoa.dylib`，Windows 需要 `qwindows.dll`
- QtWebEngineProcess 可执行文件及其附属资源（`locales/`、`resources/`、`qtwebengine_locales/`）
- Qt 样式插件和图片格式插件

迁移计划 §5.3 已承认 QtWebEngine 包含"独立进程、locale、resource、plugin 等部署资源"，但在 §7 Phase 7 中只说"更新 `SummerGDS.spec` 收集 PySide6/QtWebEngine 进程、framework、resource、locale、plugin"，未给出具体策略。对比旧版 v1 spec（`summer_gds_v1/SummerGDS.spec`），旧版同样未包含 PySide6 收集——旧版可能从未经历完整的冻结打包流程，这意味着其"正向证据"在打包维度上存疑。

PySide6 6.6+ 提供了 `pyside6-deploy` 工具和 `PyInstaller` 内置 hooks。实现时至少需要：

- `--hidden-import PySide6.QtWebEngineWidgets`
- `--hidden-import PySide6.QtWebEngineCore`
- `--hidden-import PySide6.QtNetwork` 等传递依赖
- 收集 `PySide6/plugins/` 下的平台插件

**证据**：`SummerGDS.spec:36-98`（无 PySide6 收集）；`tests/SummerGDS.spec:35-98`（相同）；`summer_gds_v1/SummerGDS.spec:13-109`（旧版同样缺失）。

### B2 — GuiSession.path_tokens 字典无线程安全保护

**严重程度**：阻塞
**类别**：correctness

当前 `GuiSession.path_tokens` 是一个普通 Python `dict`（`service.py:49`）。以下代码路径在多线程 Flask worker 中并发访问该字典而无锁保护：

- `choose_save_path()`（`service.py:117`）：写入 `self.path_tokens[token] = PathToken(...)`（`service.py:125`）
- `_resolve_path_token()`（`service.py:207-216`）：读取和条件删除 `del self.path_tokens[token]`（`service.py:212`）
- `_purge_expired_tokens()`（`service.py:218-222`）：遍历并删除，但**该方法在整个代码库中没有任何调用点**

迁移计划的文件对话框桥设计（§6.3）引入了新的复杂并发场景：Flask worker 线程等待 Qt GUI 线程完成 file dialog。在此过程中，如果另一个 API 请求（例如 frontend 自动触发的 `/api/preview/svg`）同时调用 `choose_save_path()` 或 `_resolve_path_token()`，会产生 dict 竞态：

- 一个线程在迭代 dict 时另一个线程修改 dict → `RuntimeError: dictionary changed size during iteration`
- 两个线程同时写入同一 token → 丢失一个写操作
- `_purge_expired_tokens()` 从未被调用 → path_tokens dict 可能无限增长

迁移计划 §6.3 提到"单请求互斥"（只允许同时打开一个 dialog），但 path_tokens 的写入和读取不仅发生在 dialog 桥接路径上——任何携带有效 path_token 的 save/export API 调用都会读写该字典。`single-dialog-at-a-time` 不等价于 `single-request-at-a-time`。

**证据**：`service.py:49`（无锁 dict）；`service.py:125`（写入）；`service.py:212`（条件删除）；`service.py:218-222`（未调用的清理方法）。

### B3 — KLayout 原生库与 PySide6 Qt 库的符号冲突风险未评估

**严重程度**：阻塞
**类别**：compatibility

KLayout 的 Python wheels 包含原生 C++ 扩展模块（`klayout.db`、`klayout.pya`、`klayout.lay`、`klayout.rdb` 等）。其中 `klayout.lay` 模块链接对抗 Qt 库以提供可视化功能。当前 `SummerGDS.spec` 将所有这些模块列为 `hiddenimports`（`SummerGDS.spec:62-71`）。

如果 PyInstaller 冻结包中同时包含 PySide6 的 Qt 共享库（`libQt6Core.dylib`、`libQt6Gui.dylib` 等）和 KLayout 自带的 Qt 共享库，且两者版本不同，则在运行时可能产生以下后果：

- macOS：`Namespace collision` 或 `symbol not found` 崩溃
- Windows：DLL 加载顺序导致的 `Entry Point Not Found` 错误
- Linux（未来支持）：`version 'Qt_6.X' not found` 链接错误

迁移计划没有在当前 v2 代码中明确说明是否只使用 `klayout.db` 和 `klayout.pya`（这两个模块不依赖 Qt GUI），也没有说明 `klayout.lay` 的 `hiddenimports` 是否应该从生产 spec 中移除。

需要确认：v2 生产路径是否实际需要 `klayout.lay`、`klayout.rdb`、`klayout.lib`、`klayout.pex`？如果不需要，应从 `hiddenimports` 中移除，降低冲突风险。

**证据**：`SummerGDS.spec:62-71`（klayout 全量 hiddenimports）；`tests/SummerGDS.spec:57-65`（相同模式）。

### B4 — 文件对话框桥无超时机制，关闭路径存在永久阻塞风险

**严重程度**：阻塞
**类别**：correctness

迁移计划 §6.3 描述的文件对话框桥设计中，Flask worker 线程"等待 request 完成"。但计划未定义以下关键行为：

1. 如果 Qt GUI 线程在 `QFileDialog.exec()` 过程中发生 render process crash、Qt 内部死锁或 macOS 原生对话框挂起，Flask worker 将**永久阻塞**。
2. Flask server 关闭（`handle.stop()` → `server.shutdown()`）时，如果有 worker 线程正在等待未完成的 dialog request，`thread.join(timeout=2)`（`launcher.py:55`）只能等 2 秒。如果 worker 线程在此后仍阻塞在 dialog 等待上，进程退出时会留下僵尸线程或被 `atexit` 强制终止，可能导致临时文件泄漏。
3. 计划中提到"应用关闭必须唤醒所有等待线程，禁止无限阻塞"（§6.3），但没有给出实现策略——是用 `threading.Event` + `QTimer` 超时？是用 `QApplication.aboutToQuit` 信号提前取消所有 pending request？具体代码路径未定义。

对比当前 `launcher.py` 的现有实现：`Launch_desktop()` 在 `finally` 块中调用 `handle.stop()`（`launcher.py:102-105`）。该设计中 Flask server 的 shutdown 和 session close 是确定性的。但引入 dialog bridge 后，`handle.stop()` 可能无法正常完成，因为 worker 线程正阻塞在 bridge 等待上。

**证据**：`launcher.py:55`（2 秒 join timeout）；`launcher.py:102-105`（shutdown 顺序）；迁移计划 §6.3（缺少超时策略）。

---

## 3. 高优先级发现

### H1 — LGPL 许可证合规策略缺失

PySide6 基于 LGPLv3 分发，QtWebEngine 基于 LGPLv3 或 GPLv3 或商业许可。LGPLv3 §4 和 §6 要求：

- 用户必须能够自行重新链接（relink）修改版本的 Qt 库
- 必须随分发提供或明确指引获取 Qt 源码的方式
- 必须提供安装信息和目标代码的编译说明

PyInstaller 冻结包将所有内容压入 onedir 或 onefile，用户无法方便地替换单个 `.dylib`/`.dll`。这通常需要额外提供：

- 未压缩的 onedir 布局（迁移计划已选 onedir，部分满足）
- 许可证文本和第三方 notice 文件
- 对 LGPL 的 relink 指引（如何用修改后的 Qt 库替换 bundle 中的库）

迁移计划 §5.3 和 §7 Phase 10 提及了许可证义务，但将其推迟到"正式发布前核对并记录"。鉴于 LGPL 合规是发布的法律前提，这一项应提升到 Phase 1 基线中明确记录。

**证据**：迁移计划 §5.3（"正式发布前核对并记录"）；迁移计划 §7 Phase 10（"记录应用许可证、Qt/PySide6 和第三方组件 notice"）。

### H2 — QWebEngineView 渲染进程崩溃检测与恢复策略缺失

QtWebEngine 使用独立的 Chromium 渲染进程（`QtWebEngineProcess`）。该进程可能因内存不足、GPU 驱动故障或内部 JS 错误而崩溃。`QWebEngineView.renderProcessTerminated` 信号会发出，但 `QWebEnginePage.RenderProcessTerminationStatus` 仅提供粗粒度的终止原因（`NormalTermination`、`AbnormalTermination`、`Crashed`、`Killed`），且退出代码在不同平台与 Qt 版本间含义不同。

迁移计划 §6.2 步骤 10 提到"renderer crash 或页面加载失败至少写入诊断日志"，但：

- 未说明崩溃后是否自动 reload 页面
- 未说明 reload 后是否需要重新认证 session token
- 未说明连续崩溃的上限次数（避免 crash-loop）
- 未说明崩溃期间如有 pending file dialog 请求应如何处理

对比旧版 v1 `MainWindow`（`qt_mainwindow.py`），旧版完全没有处理 `renderProcessTerminated` 信号。这意味着当前 v1 的"正向证据"在这方面是空白。

**证据**：`qt_mainwindow.py:123-127`（`_init_web_view` 未连接 renderProcessTerminated）；迁移计划 §6.2（只要求日志，无恢复策略）。

### H3 — Windows ARM QtWebEngine 可用性未确认

截至 2026 年 7 月，PyPI 上的 PySide6 官方 wheels 对 Windows ARM64（`win_arm64`）的支持仍不完整。QtWebEngine 尤其依赖 Chromium 构建基础设施，而 Chromium 对 Windows ARM64 的原生编译支持在 Qt 6.5–6.8 周期中逐步改善但尚未稳定。

迁移计划 Phase 8 设在 Windows ARM 虚拟机中验证。如果 PySide6 没有 Windows ARM64 wheels，则：

- 需要在 ARM VM 中从源码编译 PySide6（耗时数小时，需要完整的 C++ 构建工具链）
- 或者依赖 Windows x64 emulation 运行 x64 PySide6（性能损失 + 可能的兼容问题）
- 或者跳过 ARM 兼容层验证，直接进入原生 x64（失去 ARM 信号）

迁移计划 §2.4 说"计划使用 Windows 的 x86/x64 兼容能力测试相应构建"，这表明可能使用 x64 版本通过 x64 emulation 运行。这种情况下 Phase 8 测试的是 x64 emulation 而非原生 ARM。这需要明确记录，避免误读。

**证据**：迁移计划 §2.4（"Windows ARM 虚拟机" + "x86/x64 兼容能力"）；迁移计划 §7 Phase 8（"记录实际构建架构和兼容层"）。

### H4 — 无前端 JavaScript 静默失败检测机制

当前 v2 前端是单体 `app.js`，Graphify 图谱显示其包含极深的调用链（最深 6 层、最多 83 个节点——flow `static_app_handleshapeaction`，`flows.json` 第 962 行）。在 QWebEngineView 中，如果 JavaScript 抛出未捕获异常、或 DOM 操作因元素缺失而静默失败，用户看到的会是一个空白或卡死的页面，且没有任何反馈。

迁移计划 §6.4 只规定了导航安全约束，未说明如何使用：

- `QWebEnginePage.javaScriptConsoleMessage()` 将 JS 错误转发到 Python 日志
- `webChannel` 建立 JS ↔ Python 双向心跳
- 页面加载完成后的 DOM 完整性检查（如检测关键元素是否存在）

旧版 v1 `MainWindow`（`qt_mainwindow.py`）同样没有处理 `javaScriptConsoleMessage`。这意味着 v1"正向证据"在错误可见性方面存在空白。

**证据**：`qt_mainwindow.py:123-127`（无 JS console 转发）；`flows.json` `static_app_handleshapeaction` flow（83 个节点、6 层深）。

### H5 — Qt 平台插件部署策略未细化

Qt 应用在运行时通过 `QT_PLATFORM_PLUGIN` 环境变量或 `platforms/` 子目录发现平台插件。PyInstaller 需要显式配置才能将平台插件（`libqcocoa.dylib` / `qwindows.dll`）收集到正确位置。

常见陷阱：

- macOS：平台插件必须位于 `PySide6/Qt/plugins/platforms/` 相对于 bundle 根目录
- Windows：`qwindows.dll` 必须在 `platforms/` 目录，且 `QT_QPA_PLATFORM_PLUGIN_PATH` 可能需要在运行时设置
- 即使 PyInstaller 成功收集了插件，如果路径不匹配，应用启动时会静默退出或显示最小化错误对话框（--windowed 模式下可能看不到任何输出）

迁移计划 §7 Phase 7 提到"收集 PySide6/QtWebEngine 进程、framework、resource、locale、plugin"，但没有具体到平台插件的收集和路径配置。

**证据**：`SummerGDS.spec:36-98`（无平台插件配置）；`summer_gds_v1/SummerGDS.spec:13-109`（同样缺失）。

### H6 — 生产环境 Flask Werkzeug debugger 风险未设防

当前 `launcher.py` 使用 `make_server(host, 0, app, threaded=True)` 启动 Flask（`launcher.py:60`），该函数不启用 debug 模式。但如果未来开发过程中有人将 `create_app` 的配置改为 `app.config["DEBUG"] = True`，Flask 的 Werkzeug debugger 会暴露 `/console` 端点，允许在浏览器中执行任意 Python 代码。

因为桌面应用的 Flask 只监听 `127.0.0.1` 的随机端口且有 session token 保护（`server.py:33-39`），攻击面有限。但在以下场景中仍构成风险：

- 本地恶意软件扫描 localhost 端口
- session token 通过日志泄漏
- debug 模式意外留在生产 bundle 中

迁移计划没有明确要求在 `create_app()` 或 `launcher.main()` 中强制禁用 debug 模式。

**证据**：`server.py:20-29`（`create_app` 无 debug 强制关闭逻辑）；`launcher.py:60`（未传递 debug=False 显式参数）。

### H7 — 冻结包 smoke 测试缺乏自动化检查

迁移计划 §7 Phase 7 的验收标准完全依赖人工 smoke test（"断开开发服务器和终端后应用仍可启动"等 5 项）。人工 smoke 无法验证以下关键属性：

- bundle 内是否包含全部所需的 Qt 插件和 QtWebEngineProcess
- bundle 是否引用了 `.venv` 之外的库路径（`DYLD_LIBRARY_PATH` / `PATH` 泄漏）
- bundle 在被移到不同目录后是否仍能启动
- bundle 在无 Python 安装的干净机器上是否真的可运行

应增加至少一项自动化检查：在 CI 或本地脚本中构建 onedir，然后在隔离环境（`PATH` 清空、`PYTHONPATH` 清空）中执行 `dist/SummerGDS/SummerGDS --headless`（如果 plan 中实现了 headless 模式）并验证 HTTP 200。

**证据**：迁移计划 §7 Phase 7（纯人工验收）；`SummerGDS.spec:21`（MODE = "onedir"）。

### H8 — 并发 API 请求安全性未评估

Flask server 配置为 `threaded=True`（`launcher.py:60`），这意味着多个 HTTP 请求可以并发执行在 `GuiSession` 的同一实例上。当前情况下，只有 `path_tokens` 字典的无锁访问是明显的数据竞态（见 B2）。但迁移后引入了 dialog bridge，以下额外场景需考量：

- Frontend 可能在用户操作 file dialog 的同时触发 `preview_svg()`（例如自动刷新），两者均在 `GuiSession` 同一实例上操作
- `choose_save_path()` 的 side effect（写入 `path_tokens`）与 `_resolve_path_token()` 的 side effect（删除 `path_tokens`）可能交错
- `cleanup_stale_sessions()` 遍历临时目录，可能与 `preview_svg()` 的临时文件创建交叉

迁移计划 §6.3 说"同时请求不会打开多个 modal dialog"，但这只能通过 dialog 层的互斥实现，不能解决 `GuiSession` 内部状态的竞态。

**证据**：`launcher.py:60`（`threaded=True`）；`service.py:49`（无锁共享状态）。

---

## 4. 中优先级发现

### M1 — launcher.py 顶层 import PyWebviewSaveFileDialog 会阻断 Phase 过渡

`launcher.py:24` 在模块顶层导入 `from summer_gds.gui.desktop import PyWebviewSaveFileDialog`。虽然导入 `PyWebviewSaveFileDialog` 本身不立即导入 `webview`（因为 `_save_dialog_constant()` 和 `_open_dialog_constant()` 延迟导入），但如果在 Qt 迁移中间阶段 `desktop.py` 被修改或 `webview` 包被卸载，仅仅是 `import summer_gds.gui.launcher` 就会触发 `ImportError`。

迁移计划 §7 Phase 5 提到"Qt source-run 与打包 smoke 通过前保留旧 pywebview 文件，便于分阶段比较"。但保留文件不等于保留可用性——如果 `pyproject.toml` 中的 `pywebview` 依赖被移除，而 `launcher.py:24` 仍然引用，代码将不可导入。

**证据**：`launcher.py:24`（顶层导入 PyWebviewSaveFileDialog）。

### M2 — 测试假对象（FakeWindow）与 pywebview 紧密耦合

Graphify 图谱显示 `FakeWebviewModule`、`FakeWindow`、`FakeServerHandle` 均通过 INFERRED 边连接到 `PyWebviewSaveFileDialog`（`GRAPH_REPORT.md:37-43`）。当前测试完全基于 pywebview 的抽象构建（`test_launcher.py:27-51` FakeWebviewModule、`test_launcher.py:82-89` FakeWindow）。

迁移到 Qt 后，需要同等级别的 Qt dialog bridge 假对象。计划 §7 Phase 3 提到"Qt dialog bridge 单元测试"，但没有说明 `FakeWindow` 的相应替代品（如 `FakeQBridge`）的设计。

**证据**：`GRAPH_REPORT.md:37-43`（INFERRED 边）；`test_launcher.py:27-89`（pywebview 假对象）。

### M3 — Qt 版本未锁定

PySide6 的版本直接影响：

- PyInstaller hooks 的可用性和正确性（6.5 vs 6.6+ 差异显著）
- QtWebEngine 的 Chromium 版本（影响安全补丁和 JS 兼容性）
- Windows ARM64 支持状态
- macOS notarization 兼容性

迁移计划没有指定目标 PySide6 版本或版本范围。应在 `pyproject.toml` 中锁定具体版本（如 `PySide6>=6.6,<6.9` 或 `PySide6-Essentials==6.7.2`），避免 CI 和用户环境之间的版本漂移。

**证据**：迁移计划全文无 PySide6 版本号。

### M4 — start_loopback_server() 缺少就绪信号

`start_loopback_server()`（`launcher.py:59-63`）创建 server、启动 daemon 线程后立即返回，不验证 server socket 是否真正在监听。迁移计划 §6.2 步骤 8 "加载 loopback URL" 中，`QWebEngineView.setUrl()` 可能在 server 线程完成 `bind()` + `listen()` 之前执行，导致首屏加载失败。

对比 v1 `_run_qt()`（`qt_launcher.py:256-258`），旧版在创建 MainWindow 之前等待了 `server.wait_ready(timeout=10.0)`，然后再 `setUrl`。新版应继承这个模式。

**证据**：`launcher.py:59-63`（无就绪轮询）；`qt_launcher.py:256-258`（旧版有 wait_ready）。

### M5 — 运行时内存预算未量化

QtWebEngine（Chromium 渲染进程）通常消耗 100-200 MB RSS。加上 Python 进程（KLayout 原生扩展 + matplotlib + numpy），总内存可能超过 500 MB。迁移计划 §5.3 承认磁盘体积增加，但未讨论运行时内存。对低配 Windows 机器（4GB RAM）或虚拟机环境，这可能影响可用性。

**证据**：迁移计划 §5.3（只讨论磁盘体积）。

### M6 — 渲染进程崩溃的测试策略缺失

当前测试框架基于 pytest，完全在无 GUI 环境中运行。`renderProcessTerminated` 信号的触发需要真实的 QWebEngineView 实例。计划没有说明如何在 CI 中验证这项功能——是否需要 `xvfb`（Linux）或虚拟 framebuffer？是否需要特殊配置来人为触发 Chromium 进程崩溃？

**证据**：`test_launcher.py`（全为无 GUI 假对象测试）；迁移计划 §7 Phase 4（只要求"至少写入诊断日志"）。

### M7 — 日志文件无轮转策略

`_log()` 函数（`launcher.py:33-38`）每次调用都 `open(..., "a")` + `write` + 隐式 close。长期运行或多个 session 后，`~/.summer-gds-debug.log` 可能增长到无法管理的大小。迁移计划 §10 描述的日志系统没有提及轮转（rotation）、截断（truncation）或大小限制。

**证据**：`launcher.py:33-38`（无轮转）；迁移计划 §10（无轮转提及）。

---

## 5. 低优先级发现

### L1 — QWebEngineProfile 策略表述模糊

迁移计划 §6.4 说"使用独立或 off-the-record profile，避免不必要的持久 cookie/cache"。这句话给出了两个互斥的选项——独立 profile（持久）和 off-the-record profile（非持久）。应为生产构建选择一个明确的策略。

**证据**：迁移计划 §6.4。

### L2 — 未指定 QWebEngineView.loadFinished 错误处理

`loadFinished(ok)` 信号在 `ok=False` 时表示页面加载失败。计划说"页面 load started/succeeded/failed"应写入日志（§10），但没有说明 `loadFinished(False)` 后应采取什么措施——是显示错误页面？是 retry？是显示原生错误对话框？

**证据**：迁移计划 §6.2、§10。

### L3 — 路径中的中文/Unicode 字符测试未纳入矩阵

迁移计划 §9 测试矩阵中，只有 §7 Phase 8 的 Windows ARM 目视验收提到"中文路径可以打开和保存"。这个测试应作为自动测试的一部分，在 Phase 3（dialog bridge）和 Phase 6（macOS verification）中就强制执行，而非推迟到 Windows 目视验收。

当前 `service.py` 的路径处理使用 `pathlib.Path`，理论上 Unicode 安全，但没有专门的中文路径测试。

**证据**：迁移计划 §9（中文路径仅出现在 Windows ARM 目视验收）；`tests/gui/test_launcher.py`（无 Unicode 路径测试）。

### L4 — 关闭流程中对 QApplication 的 quit() 调用时机未定义

迁移计划 §6.2 步骤 10 说"退出 Qt event loop"，但没有说明是通过 `QApplication.quit()`、`QApplication.exit(0)` 还是 `QMainWindow.close()` 触发。在 macOS 上，`QApplication.quit()` 的行为与 `cmd+Q` 和 Dock 退出的交互需要验证。

**证据**：迁移计划 §6.2。

### L5 — summer_gds_v1 旧代码的删除计划未覆盖 qwebengine 下载功能

旧版 `MainWindow._handle_download()`（`qt_mainwindow.py:187-233`）使用 QWebEngine 的下载机制来保存 GDS 文件。迁移计划 §6.4 明确说"不使用 QWebEngine download 作为 YAML/GDS 保存路径"，这是正确的方向变更。但 v1 代码的清理计划中没有明确说明这个功能不迁移的原因和替代方案，可能导致未来维护者困惑。

**证据**：`qt_mainwindow.py:187-233`；迁移计划 §6.4、§13（只提到删除 `desktop.py` 和 pywebview）。

---

## 6. 要求的计划变更

以下变更必须在实施前（Phase 1）回填到迁移计划中：

1. **B1 修复**：在 §7 Phase 7 中补充 PySide6/QtWebEngine 的具体 PyInstaller 配置策略，至少包括：
   - 使用的 PySide6 钩子 API（`collect_data_files`、`collect_dynamic_libs`）
   - 平台插件收集说明
   - QtWebEngineProcess 及其附属资源的位置约定
   - 参考 PySide6 官方 PyInstaller 部署文档的链接

2. **B2 修复**：在 §6.3（或新增小节）中说明 `GuiSession` 的线程安全策略。选项包括：
   - `path_tokens` 加 `threading.Lock()` 保护
   - 或使用 `queue.Queue` 串行化所有 GUI session 状态变更
   - 明确 `_purge_expired_tokens()` 的调用时机（至少应在 `choose_save_path()` 入口调用）
   - 确认或否定是否需要 `threading.RLock` 以支持可重入

3. **B3 修复**：在 §11（风险与缓解）中增加 KLayout Qt 符号冲突风险条目。实施前确认：
   - v2 生产路径是否实际使用 `klayout.lay`（Qt 依赖模块）
   - 如果不使用，从 `hiddenimports` 移除
   - 如果使用，测试 PySide6 Qt 与 KLayout Qt 的版本兼容性并记录

4. **B4 修复**：在 §6.3 文件对话框桥设计中明确：
   - dialog request 的最大等待超时（建议 30 秒）
   - 超时后的行为（取消 request、返回错误给前端、写入警告日志）
   - 关闭时的取消协议：`QApplication.aboutToQuit` 连接 bridge 的 cancel-all 方法
   - Flask worker 在超时后不得继续操作已废弃的 request

5. **H4 修复**：在 §6.4 或新增 §6.5 中增加 JS 错误可见性策略：
   - `javaScriptConsoleMessage` → Python logging（至少 WARNING 级别）
   - 页面加载完成后 DOM 关键元素的存在性检查
   - 可选的 JS→Python 心跳（轻量级，不阻塞）

6. **H5 修复**：在 §7 Phase 7 中增加 Qt 平台插件的收集和路径配置步骤。

---

## 7. 可选改进

以下改进不阻塞迁移，但会提升质量和可维护性：

1. **O1 — 增加 headless 模式**：在 `launcher.py` 中增加 `--headless` 标志，用于 CI 中的冻结包 smoke 测试（无需虚拟显示器）。旧版 v1 已有 `--headless` 支持（`qt_launcher.py:64`），新版应继承。

2. **O2 — 锁定 PySide6 版本**：在 `pyproject.toml` 中指定精确的 PySide6 版本范围，并记录选择理由（与该版本的 QtWebEngine Chromium 基线对应）。

3. **O3 — 日志轮转**：将 `_log()` 改为使用 `logging.handlers.RotatingFileHandler`，默认 1MB/3 个备份。

4. **O4 — 启动就绪轮询**：参照旧版 `server.wait_ready()` 模式，在 `runtime.py` 的 `start_loopback_server()` 中增加一个轻量就绪检查（HTTP GET on `/` with retry）。

5. **O5 — Unicode 路径自动测试**：在 `test_launcher.py` 中增加中文/emoji/空格路径的 dialog bridge 测试。

6. **O6 — 内存基线记录**：在 Phase 1 记录当前 pywebview 的内存基线，作为 Phase 6/7 Qt 迁移后的对比基线。这比仅凭经验声称"体积增加"更有说服力。

7. **O7 — 崩溃恢复策略**：为 `renderProcessTerminated` 实现自动 reload（最多 3 次），reload 之间 exponential backoff（1s、3s、9s）。超过上限后显示原生错误对话框。

---

## 8. 实现就绪检查清单

在 Phase 0 评审通过、进入 Phase 1 前，确认以下每一项：

- [ ] B1：PyInstaller spec 中已补充 PySide6/QtWebEngine 打包策略
- [ ] B2：GuiSession 的共享状态已加锁或改为线程安全数据结构
- [ ] B3：KLayout 与 PySide6 Qt 库版本兼容性已评估并记录
- [ ] B4：File dialog bridge 已定义超时和关闭取消协议
- [ ] H1：LGPL 合规清单已起草（至少记录需要交付的 notice 文件）
- [ ] H2：renderProcessTerminated 处理策略已确定（reload / 报错 / 两者）
- [ ] H3：Windows ARM PySide6 wheels 可用性已确认并记录
- [ ] H4：JS console message → Python log 转发已纳入设计
- [ ] H5：Qt 平台插件收集策略已细化到具体文件
- [ ] H6：`create_app()` 中强制执行 `debug=False`
- [ ] M3：PySide6 版本已锁定
- [ ] M4：`runtime.py` 启动函数包含就绪轮询
- [ ] 当前 pytest 基线运行通过（84 项测试全绿）
- [ ] `summer-gds-gui` 当前入口行为已记录（启动、关闭、日志路径）

---

## 9. 计划质量评估

### 优点

- **问题定义精确**：直接锁定 `pywebview → pythonnet` 故障链，不夸大其词
- **架构约束清晰**：§6.1 的模块职责边界表规定了每个文件可以/不可以导入什么，这是正确的做法
- **范围克制**：§4 的非目标列表和 §13 的"明确不应修改"列表有效防止了范围蔓延
- **阶段门控务实**：每个 Phase 有验收标准和回滚触发条件，符合增量迁移的最佳实践
- **承认不确定性**：§2.4 和 §7 Phase 8/9 明确区分了 ARM 兼容层测试和原生 x64 发布测试，避免过度承诺
- **安全边界思考完整**：§6.4 的 12 条 WebEngine 安全约束覆盖了主要攻击面

### Graphify 图谱验证摘要

- 图谱确认了迁移范围：Community 5（launcher/desktop/pywebview hub，22 节点）是需要替换的核心区域；Community 6（GuiSession/service，39 节点）是应保持稳定的区域
- `PyWebviewSaveFileDialog` 处于 Community 5 中心位置，有 3 条 INFERRED 边到测试组件——这确认了替换该类的波及面
- 85 条 INFERRED 边（平均置信度 0.5）提示图谱中有部分关系的正确性未经人工验证——不应过度依赖图谱进行微观决策
- 旧版 v1 的 `MainWindow`（Community 2）和 v2 的 `GuiSession`（Community 5）在独立社区中，图谱验证了新旧代码的模块化隔离

---

*本评审由 DS4P 独立完成，仅写入 `docs/reviews/qt-desktop-shell-ds4p-review.md`。未修改任何其他文件。*
