# GLM 第二轮独立评审：Qt 桌面壳迁移

评审人：GLM
评审日期：2026-07-29
评审对象：`docs/planning/qt-desktop-shell-migration-plan.md`（v1.1）、
`docs/reviews/qt-desktop-shell-round1-disposition.md`
评审类型：实施可执行性第二轮评审（implementation-executability review, round 2）
评审基线：commit `dc4d0dd`（图谱基线，见 `.graphify/GRAPH_REPORT.md:22`）

依据材料：迁移计划 v1.1、第一轮处置文档、DS4P 与 GLM 第一轮评审、
`docs/diagrams/` 下四个 `.mmd`/`.svg`、`.graphify/GRAPH_REPORT.md`、
`.graphify/flows.json`、`src/summer_gds/gui/{launcher,desktop,server,service}.py`、
`src/summer_gds/gui/static/app.js`、`pyproject.toml`、`uv.lock`、根 `SummerGDS.spec`、
`tests/gui/`。Graphify CLI 不在当前 PATH；图谱证据以直接读取
`.graphify/GRAPH_REPORT.md` 与 `.graphify/flows.json` 为准（请求允许的只读方式）。

---

## 1. Overall verdict

**`READY_WITH_CHANGES`**

v1.1 与处置文档已逐项关闭 GLM 第一轮全部阻塞性与高优先级意见（见第 2 节）。
六条端到端流程的并发、生命周期、打包、平台与测试语义在绝大多数环节已收敛为
唯一契约，并附图源（`docs/diagrams/*.mmd`）与代码证据：

- 启动→就绪→加载→DOM（计划 §6.2、Phase 2）：5 秒有界 readiness probe、
  `make_server()` 同步 bind 不替代 HTTP 可达性证明，已明确。
- 文件请求→single-flight→异步 dialog→响应/token（§6.3.1/§6.3.2/§6.3.3）：
  响应表、single-flight、100 秒超时、终态原子、晚到丢弃均确定。
- 超时→关闭 dialog→晚到丢弃→gate 释放（§6.3.3 + `qt-desktop-shell-file-dialog.mmd`）：
  gate 仅在 GUI 线程完成/关闭原 dialog 后释放，超时不允许第二 modal 并存。
- 关闭→gate→drain→session 清理→quit（§6.5 + `qt-desktop-shell-shutdown.mmd`）：
  幂等 coordinator、RequestGate 503/`app_closing`、10 秒总时限、显式一次
  `session.close()` 已定义。
- 直接 import→内置 hooks→产物清单→迁移目录源无关 probe（§7.2/§7.3/§7.4）：
  反默认 `collect_all`、最小 KLayout 收集、`verify_desktop_bundle.py` 九步输入明确。
- macOS→Windows ARM x64 emulation→原生 Windows x64（§5.2、Phase 8/9、§15）：
  三类证据严格区分，结论措辞固定。

阻止判为 `READY` 的唯一原因：**Phase 2/Phase 5 之间未定义 `tests/gui/test_launcher.py`
中 pywebview 耦合测试（`FakeWebviewModule`、`FakeWindow`、`test_pywebview_save_dialog_*`、
`test_launch_desktop_forces_edgechromium_on_windows`）的移除/替换阶段**。Phase 5 删除
`desktop.py` 并移除 `pywebview` 依赖后，这些测试会在收集期或运行期失败，使 Phase 5
“全量 pytest 全绿”不可验证，并允许实施者做出相互不兼容的处置（见第 4 节 R1）。
这是“测试语义”层面的唯一阻塞项，收敛后即可进入 Phase 1。

第 5 节另列两条非阻塞测试缺口（并发 preview、RequestGate 命名测试）与两条可选加固。

---

## 2. 第一轮 closure matrix（GLM B1–B5, M1–M7, T1–T6, I1–I6）

| 编号 | 第一轮要点 | 状态 | v1.1 / 处置证据 |
| --- | --- | --- | --- |
| B1 | 并发 dialog 语义未定义 | CLOSED | §6.3.2 single-flight：第二个请求原子立即 `dialog_busy`，不排队/不阻塞/不开第二 modal；处置 D05；Phase 3 `test_second_dialog_returns_busy_without_queueing` |
| B2 | worker 超时 + 客户端断连 + 孤儿 token | CLOSED（部分建议被拒，理由可靠） | §6.3.3 `DIALOG_WAIT_TIMEOUT_SECONDS=100`（< 前端 120s，`app.js:4`），晚到丢弃；处置 D06 拒绝把同步 Flask 断连作为正确性依赖、D07 解释 token 仅在 bridge 成功返回后创建故无需回滚未发送 token；100<120 的排序使响应通常能达客户端，残余 token 由 TTL(30min)+purge-on-entry 兜底（§6.4） |
| B3 | GUI 线程异常归并 | CLOSED | §6.3.1/§6.3.3 + 处置 D08：`DialogFailure`→`dialog_error`、`canceled=false`、HTTP 200，不得伪装取消；Phase 3 `test_dialog_exception_maps_to_dialog_error` |
| B4 | profile 二选一 | CLOSED | §6.6 + 处置 D09：无 storage name 的 off-the-record profile，不落盘 |
| B5 | GUI 被其他 modal 阻塞 / 事件循环可达 | CLOSED | §6.3.3 100 秒 worker 超时覆盖“GUI 不可达”长阻塞；合并入 B2 超时契约（与第一轮建议一致） |
| M1 | matplotlib 预热落点 | CLOSED | §6.1“预热继续由 launcher.py 负责，在首批 matplotlib import 之前”；Phase 2“matplotlib 预热留在 launcher.py 顶部，不移入 runtime” |
| M2 | 依赖声明具体化 | CLOSED | §5.1 精确锁定 `PySide6==6.11.1`（meta wheel 含 Addons/QtWebEngine）、`PyInstaller==6.21.0` 独立 packaging group；Phase 5 移除生产 `pywebview`、加 `PySide6==6.11.1`；`uv.lock` 固化（处置 D13） |
| M3 | test_launcher import 更新作为 Phase 2 gate | CLOSED（acceptance 偏软，见注） | Phase 2 动作“同一提交更新 `tests/gui/test_launcher.py` 的 import 和 fakes”；但 acceptance 未显式列“test_launcher 全绿”。深层测试生命周期缺口见第 4 节 R1 |
| M4 | offscreen / 不实例化 WebEngine 策略 | CLOSED | Phase 3“bridge 测试使用 fake dialog factory 和 Qt event dispatch，不实例化 QWebEngineView，也不弹真实 modal”；Phase 4“纯 lifecycle 测试可在 offscreen 环境、无 WebEngine 实例下运行” |
| M5 | 源码对产物校验门 | CLOSED | §7.4 `verify_desktop_bundle.py` 九步：TOC/warnings、Qt 资源、无 webview/pythonnet/clr、静态资源 SHA-256、动态库无开发机绝对路径、迁移到含空格/中文目录、净化环境、等 app-ready、固定 YAML→SVG→GDS probe + 清理断言 |
| M6 | PyInstaller 收集策略 | CLOSED（调整：拒收 GLM 建议的 `collect_all` 基线） | §7.2 直接 import 五个 Qt 模块 + 锁定版内置 hooks 为默认，禁默认 `collect_all`，漏项才加最小补项且需失败证据+自动断言；处置 D16 给出拒收理由 |
| M7 | 关闭“停止接受新请求”机制 | CLOSED | §6.5 coordinator 八步序列 + `RequestGate.begin_shutdown()`/`wait_drained()`；`server.py` 用 `before_request`/`teardown_request` 接入 |
| T1 | 启动路径不导入 webview/pythonnet/clr 的测试 | CLOSED | Phase 5 自动验收“干净子进程导入/运行 GUI 入口时阻断 `webview`、`pythonnet`、`clr_loader` 仍能到达 Qt 启动边界” |
| T2 | CLI 不导入 PySide6 的测试 | CLOSED | Phase 5“另一干净子进程导入 `summer_gds.cli`，断言未加载任何 `PySide6` 模块”（已核实 `src/summer_gds/cli.py` 不含 PySide6/webview/gui 引用） |
| T3 | 桥并发/超时/异常/关闭唤醒测试用例 | CLOSED | Phase 3 命名测试：`test_second_dialog_returns_busy_without_queueing`、`test_dialog_timeout_precedes_frontend_timeout`、`test_late_selection_after_timeout_is_discarded`、`test_dialog_exception_maps_to_dialog_error`、`test_shutdown_wakes_pending_dialog`、`test_only_one_modal_exists` |
| T4 | 静态资源本地性测试 | CLOSED | §6.6“解析 HTML/CSS/JS 引用；允许相对资源和本次 loopback，禁止公网依赖，不能用简单 `http://` 误伤 loopback”；Phase 6 列入；现有 `tests/gui/test_static_frontend.py:11-25` 已断言无 `http(s)`/`cdn` |
| T5 | macOS bundle 自动产物断言 | CLOSED | §7.4 自动 gate（同 M5）；处置 D17 拒绝全局 `strings \| grep /Users/`，改用 TOC+动态库解析+hash+迁移目录+真实启动 |
| T6 | “84 项测试”口径 | CLOSED | §2.4“只记录为 pytest `collected items`，不称为测试函数数”；Phase 1“记录 collected items/pass” |
| I1 | 两个 SummerGDS.spec | CLOSED | §7.1 根 spec 唯一权威；`tests/SummerGDS.spec` untracked，不删除/修改/提交（已核实根 spec tracked、`tests/SummerGDS.spec` 为 untracked 副本） |
| I2 | teardown 永不触发 close | CLOSED | §6.7 + 处置：`SUMMER_GDS_CLOSE_ON_TEARDOWN` 未设置（已核实 `server.py:130-133` 且全仓未设该配置），Qt coordinator 显式一次 `session.close()` |
| I3 | v1 对话框模式非桥前例 | CLOSED | §2.3 明确 v1 保存走 `downloadRequested`、非当前桥；不复用 v1 页面/API/协议 |
| I4 | Phase 2 与 Phase 1“全绿”冲突 | CLOSED | 同 M3，Phase 2 同提交更新 import |
| I5 | 图谱新鲜度作为 Phase 1 检查 | CLOSED | Phase 1“校验 Graphify report commit、当前 `HEAD` 和工作树差异；实现前图谱使用 `dc4d0dd` 基线”；`GRAPH_REPORT.md:22-23` 标注 commit 与 freshness 提示 |
| I6 | flows.json 作为证据引用 | CLOSED（非阻塞建议） | §16 关联资料列出 Graphify flows；`flows.json` 含 `flow:gui_service_guisession_choose_save_path`/`open_yaml`/`save_yaml`/`export_gds`，入口即 `file_dialog.choose_*`，佐证桥为协议 drop-in |

小结：GLM 第一轮 24 项全部 CLOSED（M3 acceptance 偏软但步骤存在；M6 按更保守策略
调整并给出理由）。无第一轮遗留 blocker。

---

## 3. Remaining blocking ambiguities

None。

第 4 节 R1 属“缺失实施步骤”而非“契约二义”，故本节为 None。

---

## 4. New contradictions or missing implementation steps

### R1（阻塞）— pywebview 耦合的 launcher 测试在 Phase 2/Phase 5 之间无确定的移除/替换阶段

`tests/gui/test_launcher.py` 当前与 pywebview 强耦合：

- `test_launcher.py:7` `from summer_gds.gui.desktop import PyWebviewSaveFileDialog`
- `test_launcher.py:8` `from summer_gds.gui.launcher import launch_desktop, start_loopback_server`
- `test_launcher.py:27-51` `FakeWebviewModule`、`test_launcher.py:64-79`
  `test_launch_desktop_forces_edgechromium_on_windows`（断言 `gui=="edgechromium"`，
  pywebview 专属行为）
- `test_launcher.py:82-136` `FakeWindow` 与三个 `test_pywebview_save_dialog_*`（直接测
  `desktop.py` 的 `PyWebviewSaveFileDialog`）

计划对这些测试的生命周期定义不一致：

1. Phase 2 动作“同一提交更新 `tests/gui/test_launcher.py` 的 import 和 fakes”落在
   **shell 仍为 pywebview** 的阶段（Qt shell 在 Phase 4/5 才实现）。此时
   `FakeWebviewModule`/`FakeWindow` 仍有效，“更新 fakes”语义不明——实施者无法判断
   Phase 2 应把 fakes 改成什么。
2. Phase 5 动作“`launcher.py` 切换为 Qt shell”“移除生产 dependency `pywebview`”
   “通过后删除 `desktop.py` 和生产路径 pywebview import”。一旦 `desktop.py` 被删，
   `test_launcher.py:7` 的 import 在收集期即 `ImportError`，整文件无法收集；即便
   临时保留 `desktop.py`，`test_pywebview_save_dialog_*` 运行期会触发
   `desktop.py:32/39` 的惰性 `import webview` 而 `ImportError`（pywebview 已从依赖移除）。
3. Phase 5 acceptance 要求“全量 pytest 和新增 Qt 专项全绿”，但全文未声明这些
   pywebview 测试在哪个阶段、以何种 Qt 等价测试替换/删除。§14“预计修改
   `tests/gui/test_launcher.py`”也未细化。

后果：实施者可能 (a) 在 Phase 2 过早把 fakes 改成 Qt fakes（shell 尚非 Qt，测试无意义）、
(b) 保留 pywebview 测试直到 Phase 5 再整体替换、(c) 为保测试绿而暂不删 `desktop.py`
（违反“通过后删除”）。三种路径产物不同，且 Phase 5“全量 pytest 全绿”在该决策缺位下
不可验证。这正是评审目标中“不得自行发明测试语义”的命中项。

非阻塞的相关观察：

- `test_launcher.py:12-24` 的 `test_loopback_server_serves_gui_and_stops` 只依赖
  `start_loopback_server`+`create_app`，迁移到 `runtime` 后可保留（仅需改 import），
  不受 R1 影响。

---

## 5. Missing or weak tests or gates

以下为非阻塞测试缺口与可选加固，建议在对应 Phase 补齐（不阻塞 Phase 1）。

### T-R1（与第 4 节 R1 同源，阻塞）— Phase 5 需命名“pywebview launcher 测试替换”测试集
见第 4 节。需在 Phase 5 显式列出 Qt launcher 的等价测试（或显式声明删除 pywebview 专属
测试），否则 Phase 5 不可验证。

### T-R2（非阻塞）— 并发 preview 测试未进入 Phase 3 命名清单
§6.4 与 §10 测试矩阵均要求“增加并发 preview 测试，确保不同 ID 不互相删除”，但 Phase 3
的命名测试清单未包含该项。建议补 `test_concurrent_preview_with_distinct_request_ids_does_not_clobber`。
（preview 临时文件按 `_stable_request_id` 命名，`service.py:90-91/263-264`，语义已定，
仅清单缺名。）

### T-R3（非阻塞）— RequestGate 的 503/drain 行为无命名测试
§6.5 定义了 `RequestGate` 的 enter/leave/`closing`/`wait_drained` 与 503 `app_closing`，
但 §10“runtime”行只覆盖 bind/ready/stop/timeout/幂等（loopback server），Phase 4
lifecycle 测试以“唯一 shutdown”概括，未点名 gate 的 503 与 drain-only-entrenched 语义。
建议在 Phase 2 或 Phase 4 补：
`test_request_gate_rejects_new_api_with_503_after_begin_shutdown`、
`test_request_gate_wait_drained_returns_only_after_in_flight_converge`。
（语义已定，仅为可验证性补命名测试。）

### T-R4（可选加固）— bundle gate 未显式自动化“无第二套 Qt”断言
§7.3 要求“产物不得出现由 KLayout 额外带入的另一套 Qt”，但 §7.4 九步只含动态库绝对路径
检查（step 5），未含“重复 Qt 库”自动断言；当前以 §7.3 的 `otool -L`/`dumpbin` 记录为
人工/半自动证据。鉴于生产源码仅 `import pya`（非 Qt 模块），风险低；建议在
`verify_desktop_bundle.py` 增加一步：断言产物内 `Qt6Core/Qt6WebEngineCore` 等关键 Qt 库
唯一来源（无 KLayout 自带副本）。

### T-R5（可选加固）— `QT_QPA_PLATFORM=offscreen` 未显式写入测试环境要求
Phase 3/4 多次提到“offscreen 环境”“不实例化 QWebEngineView”，但未显式要求在
`conftest`/pytest 环境设置 `QT_QPA_PLATFORM=offscreen`。建议在 Phase 3 显式声明该环境
变量要求，避免 CI 无显示机下 bridge/shell 测试因平台插件缺失而误红。

---

## 6. Evidence（仓库路径与行号）

### 启动 / 就绪
- `launcher.py:15-19` matplotlib 预热（顶层，先于其他 matplotlib import）——支撑 M1。
- `launcher.py:59-63` `start_loopback_server`（`make_server(host,0,app,threaded=True)`，
  daemon 线程）；`launcher.py:55` `join(timeout=2)`——Phase 2 迁入 `runtime.py` 并加
  5 秒 readiness probe。
- `launcher.py:24` 顶层 `from summer_gds.gui.desktop import PyWebviewSaveFileDialog`——
  Phase 5 切换 Qt 后该 import 须移除；其连带测试影响见 R1。
- `launcher.py:102-105` `finally: handle.stop(); session.close()`——现有确定性关闭，
  Qt 路径须由 coordinator 显式复刻（§6.5/§6.7）。

### 文件对话框 / 响应语义
- `service.py:117-136` `choose_save_path`：`service.py:125` 写入 `path_tokens[token]`；
  成功返回 `{ok:true, path_token, path_label, exists, errors}`，取消返回
  `{ok:false, canceled:true, errors:[]}`——与 §6.3.1 表一致。
- `service.py:207-216` `_resolve_path_token`（读 + 过期删除 + kind 校验）；
  `service.py:218-222` `_purge_expired_tokens`（**当前无调用点**，§6.4 要求在
  `choose_save_path` 入口/选择后接入）。
- `service.py:46` `path_token_ttl_seconds=30*60`；`service.py:49` `path_tokens: dict`
  （§6.4 要求加普通 `Lock`）。
- `app.js:4` `FILE_DIALOG_TIMEOUT_MS=120000`、`app.js:2` `REQUEST_TIMEOUT_MS=15000`；
  `app.js:2063-2106` `postJson` + `AbortController` 超时——支撑 100<120 排序（B2）。
- `app.js:1709-1712` choose-save `!choice.ok` 时按 `choice.canceled` 分流并
  `renderApiErrors(choice.errors||[])`——前端已能区分取消与 busy/timeout/error，与
  §6.3.1/处置 §4 一致（Phase 3 仅需补 busy/timeout/error 文案）。
- `app.js:2054-2061` `handleRequestError` 处理 `AbortError`/`TimeoutError`——网络层异常
  兜底，与“后端 100s 先结束”配合。

### 关闭 / RequestGate
- `server.py:33-39` `before_request` token 校验（§6.5 `RequestGate` 接入点同处）。
- `server.py:130-133` `close_session` teardown 仅在 `SUMMER_GDS_CLOSE_ON_TEARDOWN`
  为真时关 session；全仓未设该配置（已核实）——支撑 I2，Qt 路径须显式 `session.close()`。

### 打包 / 依赖
- `pyproject.toml:5-11` 依赖含 `pywebview>=5.0`，无 PySide6/PyInstaller；
  `pyproject.toml:13-16` dev 组仅 `pytest`（packaging group 待 Phase 1 新建）；
  `pyproject.toml:18-20` `summer-gds-gui = summer_gds.gui.launcher:main`（不变）。
- `uv.lock:288-289` KLayout `0.30.8`；其 wheels 含 `win32`/`win_amd64`、无
  `win_arm64`（`uv.lock:298-299`）——支撑 §5.2 Windows 交集仅 AMD64。
- `uv.lock` 无 `pyside6`/`pyinstaller` 包条目（已核实）——Phase 1/5 需新增并锁定。
- `SummerGDS.spec:62-71` hiddenimports 含 `klayout.lay/rdb/lib/pex`（§7.3 要求删除）；
  `SummerGDS.spec:92` `collect_submodules("klayout")`（§7.3 要求删除）；
  `SummerGDS.spec:49/55/101` klayout/matplotlib data + klayout dynamic_libs；
  `SummerGDS.spec:26` `MODE="onedir"`；`SummerGDS.spec:5-7` 记录 pythonnet/clr 故障——
  迁移动机证据。
- `SummerGDS.spec` 无任何 PySide6 收集（§7.2 要求改为直接 import + 内置 hooks）。

### 测试
- `tests/gui/test_launcher.py:7-9`（imports）、`:27-51`（FakeWebviewModule）、
  `:64-79`（edgechromium 测试）、`:82-136`（FakeWindow + 3 个 pywebview dialog 测试）
  ——R1 证据。
- `tests/gui/test_file_output_api.py:133-145` `test_yaml_save_requires_force_for_existing_file`
  用同一 token 先 blocked 后 `force=True` 成功——**已证 token 在 TTL 内可复用**，支撑
  §6.4“目标存在→确认→force 重试”复用契约（Phase 3 `test_force_retry_can_reuse_valid_token`
  在桥层补强）。
- `tests/gui/test_static_frontend.py:11-25` 已断言 `index.html` 无 `http(s)`/`cdn` 且含
  本地 `/static/...`——T4 已有回归门雏形。

### 图谱
- `.graphify/GRAPH_REPORT.md:22-23` commit `dc4d0dd` + freshness 提示；`:9` 1047 节点/
  1947 边/53 社区；`:37-42` 三条 `Fake*/PyWebviewSaveFileDialog` INFERRED 边——印证
  R1 的波及面。
- `.graphify/flows.json` 含 `flow:gui_service_guisession_choose_save_path`、
  `..._open_yaml`、`..._save_yaml`、`..._export_gds`，入口即 `file_dialog.choose_*`——
  印证桥为协议 drop-in、业务层不变（I6）。

### 图
- `docs/diagrams/qt-desktop-shell-target-architecture.mmd`、`-file-dialog.mmd`、
  `-shutdown.mmd`、`-migration-gates.mmd` 及对应 `.svg` 均存在并与 §6/§9 文本对应；
  `file-dialog.mmd:21-27` 与 §6.3.3 超时/晚到丢弃一致；
  `shutdown.mmd` 与 §6.5 八步一致（图将“拒绝新 dialog+API”合并为首步，文本分列 step 3/4，
  差异为简化，非矛盾——见第 4 节末）。

---

## 7. Exact wording / acceptance changes for every blocking issue

### R1（阻塞）— 补 Phase 5 测试置换步骤，并校正 Phase 2“fakes”措辞

在 Phase 2 动作中，将：

> 同一提交更新 `tests/gui/test_launcher.py` 的 import 和 fakes。

改为：

> 同一提交更新 `tests/gui/test_launcher.py` 的 import：`LoopbackServerHandle`/
> `start_loopback_server` 改自 `summer_gds.gui.runtime`（或在 `launcher` 重新导出）。
> 本阶段**仅**更新 import 与 `FakeServerHandle` 以匹配新 runtime 形状；`FakeWebviewModule`、
> `FakeWindow` 及 `test_pywebview_save_dialog_*` 等 pywebview 专属测试**保留不动**
> （此时 shell 仍为 pywebview）。Phase 2 acceptance 增加：“`test_launcher.py` 可被收集
> 且 `test_loopback_server_serves_gui_and_stops` 通过。”

在 Phase 5 动作中，新增一条：

> 在 `launcher.py` 切换为 Qt shell、`pywebview` 移出依赖的同一提交中，处置
> `tests/gui/test_launcher.py` 的 pywebview 专属测试：删除 `FakeWebviewModule`、
> `FakeWindow`、`test_launch_desktop_forces_edgechromium_on_windows` 与全部
> `test_pywebview_save_dialog_*`，并删除 `from summer_gds.gui.desktop import ...`；
> 以 Qt launcher 的等价测试替换（如 `test_launcher_starts_qt_shell_under_offscreen`、
> `test_launcher_does_not_import_webview_or_pythonnet`，使用 fake Qt shell/fake dialog，
> 不实例化 `QWebEngineView`）。保留 `test_loopback_server_serves_gui_and_stops`。
> `desktop.py` 删除后 `test_launcher.py` 必须仍可收集且全绿。

Phase 5 acceptance 增加：

> “`tests/gui/test_launcher.py` 不再引用 `summer_gds.gui.desktop` 或 `webview`；
> 全量 pytest（含替换后的 Qt launcher 测试）收集并通过。”

### 第 5 节非阻塞项的建议措辞（非 Phase 1 前置，供对应 Phase 采纳）

- **T-R2**：Phase 3 测试清单追加
  `test_concurrent_preview_with_distinct_request_ids_does_not_clobber`（并发发起两个
  不同 `request_id` 的 preview，断言两者临时文件互不删除、均正常返回）。
- **T-R3**：Phase 2（或 Phase 4）追加
  `test_request_gate_rejects_new_api_with_503_after_begin_shutdown`、
  `test_request_gate_wait_drained_returns_only_after_in_flight_converge`。
- **T-R4**：§7.4 增加一步“断言产物内关键 Qt 库（`Qt6Core`、`Qt6WebEngineCore` 等）唯一
  来源，不存在 KLayout 自带的第二套 Qt”。
- **T-R5**：Phase 3 显式声明“bridge/shell 单测必须在 `QT_QPA_PLATFORM=offscreen` 下可跑，
> 并在 `conftest` 或测试环境固化该变量”。

---

## 8. Final ordered implementation checklist（按计划阶段）

按依赖顺序排列；标注阶段与对应上文编号。Phase 1 前置仅 R1（阻塞），其余为对应 Phase 的
补强。

1. **[Phase 0]** 本第二轮评审无第一轮遗留 blocker；仅 R1 需在进入 Phase 1 前回填措辞。
2. **[Phase 1]** 核对 `.graphify/GRAPH_REPORT.md:22` commit `dc4d0dd` 与 `HEAD`；记录
   pytest `collected items` 基线（口径明确）；确认根 `SummerGDS.spec` 唯一权威、保护
   untracked `tests/SummerGDS.spec`；新建 packaging dependency group 并让 `uv.lock`
   精确记录 `PySide6==6.11.1`/`PyInstaller==6.21.0`/KLayout `0.30.8`；起草许可证
   inventory。（T6/I1/I5/M2/D13/D18）
3. **[Phase 2]** 迁 `LoopbackServerHandle`/`start_loopback_server` 入 `runtime.py`；
   加 5 秒有界 readiness probe + stop 幂等；`runtime.py` 不导入 PySide6/pywebview/
   matplotlib；matplotlib 预热留 `launcher.py` 顶部。**按 R1 措辞**仅更新
   `test_launcher.py` import 与 `FakeServerHandle`，保留 pywebview 专属测试；acceptance
   加“`test_launcher.py` 可收集且 `test_loopback_server_serves_gui_and_stops` 通过”。
   （M1/M3/M4/M7/I4）补 **T-R3** 的 RequestGate 命名测试。
4. **[Phase 3]** 实现 `qt_dialog.py`（single-flight、异步 `QFileDialog`、100s 超时、
   晚到丢弃、异常 marshalling、shutdown cancel）+ `DialogFailure` 响应映射 +
   `GuiSession.path_tokens` 普通 Lock 与 purge 接入；前端 busy/timeout/error 文案更新，
   保持 120s fetch 超时。按 §6.3 命名测试集 + **T-R2** 并发 preview 测试；bridge 测试
   fake dialog + Qt dispatch，不实例化 `QWebEngineView`。按 **T-R5** 固化
   `QT_QPA_PLATFORM=offscreen`。（B1/B2/B3/B5/T3/D02/D05/D07/D08）
5. **[Phase 4]** 实现 `qt_shell.py`：QApplication/off-the-record profile/受限 page/view/
   window；导航/权限/新窗口/download 限制；JS console 转发、load/DOM check、renderer
   termination、原生错误；§6.5 唯一 shutdown coordinator，显式一次 `session.close()`；
   `setQuitOnLastWindowClosed(False)` + `aboutToQuit` 兜底。offscreen 纯 lifecycle 测试
   + 静态资源本地性测试（沿用 `test_static_frontend.py`）。（B4/M4/M7/I2/D09/D10/D11/D12）
6. **[Phase 5]** `launcher.py` 切 Qt shell；`pyproject.toml` 移除 `pywebview`、加
   `PySide6==6.11.1`、packaging group 加 `pyinstaller==6.21.0`；`uv.lock` 同步；
   **按 R1 措辞**同提交处置 `test_launcher.py` pywebview 专属测试（删/换），保留
   loopback 测试；新增 import-boundary 子进程测试（GUI 入口阻断 webview/pythonnet/
   clr_loader 到达 Qt 边界；CLI 不导入 PySide6）；门槛全过后删 `desktop.py` 与
   pythonnet/clr 诊断说明；不增双壳 CLI。（M2/T1/T2/D13）
7. **[Phase 6]** macOS 本机 `uv sync --frozen` → `uv run pytest -q` → runtime/bridge/
   session lock/shell lifecycle/静态资源/production Flask 配置测试 → 真实窗口 smoke
   （base/via/rings、SVG preview、保存/打开 YAML、导出 GDS、各取消一次、中文/emoji/
   空格路径、关闭、检查无残留）；记录冷启动/稳定内存趋势基线。
8. **[Phase 7]** 按 §7 修改根 `SummerGDS.spec`（直接 import + 内置 hooks，删
   `collect_submodules("klayout")` 与 `klayout.lay/rdb/lib/pex`，最小 KLayout 收集 +
   GDS smoke）；构建 windowed onedir；运行 `verify_desktop_bundle.py`（九步 + **T-R4**
   无第二套 Qt 断言）；从仓库外 Unicode/空格目录启动 + 真实窗口目视；记录 bundle 大小/
   冷启动/稳定内存；pytest 与 `document-diagrams` freshness 同时通过。（B1-packaging/
   M5/M6/T5/D01/D03/D16/D17）
9. **[Phase 8]** Windows 11 ARM：AMD64 Python/wheels 构建 AMD64 onedir；pytest；bundle
   inventory/动态依赖/ready/YAML-SVG-GDS probe；Defender 扫描与退出清理；用户目视
   （窗口/字体/DPI/modal 前置/中文路径/preview/GDS/关闭无残留）。结论固定为“x64
   emulation 路径通过/失败”，不写 native ARM/原生 x64。（D14）
10. **[Phase 9]** 干净原生 Windows 11 x64：无 Python/.NET/开发工具、普通用户、离线、
    中英文/Unicode 路径、安装/升级/卸载、GUI 工作流与 shutdown、Defender/SmartScreen、
    VC++ runtime 由产物/安装器处理、动态依赖/签名/bundle inventory 可审计。通过后方可
    声明 Windows x64 正式兼容。
11. **[Phase 10]** 选安装器、封装 onedir、创建入口/卸载、VC++ runtime 部署、完成许可证
    inventory/notices/合规、更新 `README.md`/`docs/frontend/*`/测试策略、删除
    pywebview/pythonnet 用户文档。（D18/D20）

---

### 评审小结

方向正确，v1.1 与处置文档已逐项关闭 GLM 第一轮 24 项意见，六条端到端流程的并发/
生命周期/打包/平台/测试语义基本收敛为唯一契约且可追溯至代码与图谱。唯一阻塞项为
**R1：pywebview 耦合 launcher 测试在 Phase 2/5 间的移除/替换阶段缺失**，属测试语义
缺口，使 Phase 5“全量 pytest 全绿”不可验证。按第 7 节 R1 措辞回填后即可判 `READY`
并进入 Phase 1。第 5 节 T-R2/T-R3/T-R4/T-R5 为对应 Phase 的非阻塞补强。

*本评审由 GLM 独立完成，仅写入
`docs/reviews/qt-desktop-shell-glm-round2-review.md`。未修改任何其他文件。*
