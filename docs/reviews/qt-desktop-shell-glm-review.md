# GLM 独立评审：Qt 桌面壳迁移计划

评审者：GLM
评审日期：2026-07-29
评审对象：`docs/planning/qt-desktop-shell-migration-plan.md`（v1.0，分支 `codex/qt-desktop-shell`）
依据材料：迁移计划、`.graphify/GRAPH_REPORT.md`、`.graphify/flows.json`、
`src/summer_gds/gui/{launcher,desktop,server,service}.py`、`tests/gui/`、
`pyproject.toml`、`SummerGDS.spec`、`summer_gds_v1/web_gui/qt_{launcher,mainwindow}.py`，
以及只读仓库命令（`grep`、`graphify`）。

评审类型：实施可执行性评审（implementation-executability review）。

---

## 1. Overall verdict

**`READY_WITH_CHANGES`**

结论依据：

- 计划结构完整，阶段（Phase 0–10）划分清晰，每个阶段都有交付物与验收门槛，
  且绝大多数阶段可映射到具体仓库文件。
- 依赖方向经图谱与代码核对是干净的：`app/`、`schema/`、`geometry/`、
  `writer/` 均不导入 `summer_gds.gui` / `webview` / `PySide6`
 （`grep` 验证为空）。`GuiSession` 仅依赖 `SaveFileDialog` protocol，
  这一点也被 Graphify 社区 15（`choose_path`、`FakeSaveDialog`、
  `PathToken`）佐证——对话框桥是协议的 drop-in 实现，业务层无需改动。
- 旧版（v1）证据被诚实地限定为“QtWebEngine 承载本地 Web UI 的桌面壳模式”，
  未夸大为对话框桥的前例。
- macOS-first / Windows-later 顺序明确，且显式禁止用 ARM 兼容层替代原生 x64
  发布门槛——这是该计划的一个优点。

阻止判为 `READY` 的原因：文件对话框线程桥的核心并发契约存在多处可被实施者
多种解读的空白（并发请求语义、worker 等待超时与客户端断连、跨线程异常归并），
且 PyInstaller 资源收集与“源码对产物”校验门缺少可执行的具体步骤与自动测试。
这些不是方向性错误，但在实施前必须用确定措辞收敛，否则不同实施者会得到不同
行为。详见第 2、3、4 节。

---

## 2. Blocking ambiguities

以下各项若不收敛，实施者会做出相互不兼容的实现选择，且无法用统一测试判定对错。

### B1. 并发文件对话框请求的语义未定义

Flask server 以 `threaded=True` 启动（`launcher.py:60`、`service.py` 经
`server.py` 路由）。因此两个 API 调用（例如 `/api/file/choose-save` 与
`/api/yaml/open`，或两次保存）可能同时由两个 worker 线程进入
`GuiSession.choose_save_path()` / `open_yaml()`，进而同时进入对话框桥。

计划 §6.3 与 Phase 3 只说“单请求互斥”和“同时请求不会打开多个 modal dialog”，
但未定义第二个并发请求的行为是：

- (a) 阻塞排队，等前一个完成后再打开自己的对话框；
- (b) 立即返回一个 `canceled`/`busy` 响应，不打开对话框；
- (c) 抛出错误响应。

这三种行为对前端 `app.js` 的处理路径完全不同，且会影响是否存在“一个 worker
持锁等待、另一个 worker 持锁等待”的死锁面。

**需收敛为唯一契约。** 见第 6 节建议措辞 B1。

### B2. Worker 等待超时与“客户端在对话框打开期间断连”未处理

前端对文件对话框 API 设置了硬超时 `FILE_DIALOG_TIMEOUT_MS = 120000`
（`app.js:4`，经 `postJson` 的 `AbortController` 实现，`app.js:2066-2104`）。
桥的设计是 Flask worker 线程阻塞等待 GUI 线程完成 `QFileDialog`。

未定义的两点：

1. Worker 侧等待 GUI 完成是否有超时？计划只说“应用关闭必须唤醒所有等待线程，
   禁止无限阻塞”——这只覆盖关闭路径，不覆盖“用户把对话框开着去喝咖啡”的
   长阻塞路径。
2. 当客户端在 120s 超时后 `abort()` 并断开 HTTP 连接时，Flask worker 线程
   仍阻塞在桥的 `Event` 上，**客户端断连不会中断该阻塞**。此时：
   - worker 线程成为孤儿，持续占用一个 server 线程；
   - 若用户随后在对话框中点了“保存”，桥会向一个已死的 HTTP 响应回写
     `path_token`，该 token 随后在 `path_tokens` 中滞留至 30 分钟 TTL
     （`service.py:46`）过期。

计划未规定客户端断连/超时与桥的交互。这是一个真实的并发缺陷面，而非边缘
理论问题，因为 120s 超时是前端默认行为。

**需收敛：** worker 等待是否设超时、客户端断连是否取消 pending 请求、
孤儿 token 是否在请求失败时立即清除。见第 6 节 B2。

### B3. GUI 线程异常如何归并回 Flask worker 线程未规定

`QFileDialog` 在 GUI 线程执行；若其抛异常（原生对话框错误、权限错误、
路径异常），异常发生在 GUI 线程，无法跨线程 `raise` 到阻塞中的 Flask worker。
计划 §6.3 与 Phase 3 提到“异常传播”，但未规定：

- 异常以何种结构通过结果通道回传（error 字段？特定 `code`？）；
- Flask 路由最终返回什么 HTTP 状态与 JSON 体（当前 `choose_save_path` /
  `open_yaml` 只会返回 `{ok, canceled, errors}` 或 `{ok, path_token,...}`，
  没有“对话框自身出错”的响应形态）；
- 是归并进现有 `errors` 列表（`issue_to_dict`）还是新的错误码。

不收敛的话，实施者可能选择“吞掉异常返回 `canceled`”，这会把真错误伪装成
用户取消——难以诊断。

### B4. `QWebEngineProfile` “独立或 off-the-record”二选一未定

§6.4 写“使用独立或 off-the-record profile”。“独立持久 profile”与
“off-the-record（非持久）”是两种相反的语义：前者会落盘 cookie/cache/设置，
后者不落盘。这直接影响“避免不必要的持久 cookie/cache”这一条的可验证性，
也影响后续是否需要清理 profile 目录。需明确选定 off-the-record（与安全约束
一致），或给出何时用持久 profile 的条件。

### B5. 桥的“单请求互斥”与 GUI 线程被其他 modal 阻塞的交互未提

§6.3 列出要避免“持有全局锁时打开 modal dialog”和“GUI thread 等待 Flask
worker”。但若 GUI 线程正阻塞在**另一个** modal（例如启动错误 `QMessageBox`、
或未来的帮助对话框）上，queued signal 不会被处理，等待中的 worker 会一直
阻塞。计划未要求“GUI 线程事件循环可达”作为前置假设，也未要求 worker 等待
具备超时兜底（与 B2 同源）。建议合并到 B2 的超时契约中一并解决。

---

## 3. Missing implementation steps

### M1. matplotlib 预热的落点未指定

`launcher.py:15-19` 在模块顶层强制 `matplotlib.use("Agg")` 并预热线程不安全
的字体/后端缓存，注释说明这是为避免 PyInstaller 冷启动长停顿。计划把
`LoopbackServerHandle`/`start_loopback_server` 移到 `runtime.py`，并让
`launcher.py` 改为启动 Qt shell，但未说明这段 matplotlib 预热迁往何处
（留在 `launcher.py`？移到 `qt_shell.py`？`runtime.py` 不允许导入 PySide6
但可以导入 matplotlib）。若实施者把预热漏掉或放错位置，冷启动停顿会回归。

**补充步骤：** 在 Phase 2 或 Phase 4 明确 matplotlib 预热代码的归属模块，
并保留“必须在首批 matplotlib 导入前执行”的约束。

### M2. PySide6 / QtWebEngine 依赖声明未具体化

Phase 5 只说“增加 PySide6 和 QtWebEngine 所需依赖”。`pyproject.toml` 当前
仅声明 `pywebview>=5.0`。需明确：

- 依赖名是 `PySide6` 还是 `PySide6-Essentials` + `PySide6-Addons`
 （QtWebEngine 在 Addons 里）；
- 是否钉版本范围（QtWebEngine 与 PySide6 必须同版本）；
- `pywebview` 是从 `dependencies` 删除还是移到可选 `dev` 组用于回滚比较
 （§5 与 Phase 5 说“保留旧 pywebview 文件便于比较”，但依赖若仍在主
  `dependencies`，Phase 5 验收“正常启动路径不导入 webview”会被环境
  干扰）。

**补充步骤：** Phase 5 增加“在 `pyproject.toml` 声明 `PySide6>=6.x`，
将 `pywebview` 移至 dev/可选组或删除”的显式动作与版本钉。

### M3. `tests/gui/test_launcher.py` 的 import 更新未列为 Phase 2 验收门

`test_launcher.py:7-8` 直接 `from summer_gds.gui.launcher import ...
start_loopback_server` 并 `from summer_gds.gui.desktop import
PyWebviewSaveFileDialog`。Phase 2 把 `start_loopback_server`/
`LoopbackServerHandle` 移到 `runtime.py` 后，这些 import 会立即失败。§13
“预计修改 `tests/gui/test_launcher.py`”承认了这点，但 Phase 2 的“验收”
小节只列了 `runtime.py` 不导入 PySide6、server 测试通过、端口关闭，**未把
“测试 import 已更新且通过”作为该阶段 gate**。结果是 Phase 2 完成时基线会
红，与 Phase 1“测试全绿”矛盾。

**补充步骤：** Phase 2 验收增加“`tests/gui/test_launcher.py` 改从
`runtime` 导入 `LoopbackServerHandle`/`start_loopback_server` 且全绿”。

### M4. CI/无头测试下的 `QApplication` 平台策略缺失

Phase 6 要求“Qt dialog bridge 单元测试”和“Qt shell 生命周期测试”。在
无显示的 CI（macOS 无窗口、Linux runner）上运行 Qt 需
`QT_QPA_PLATFORM=offscreen`，而 `QWebEngineView` 在 offscreen 下并非所有
平台都可用。计划未规定：

- bridge 单测是否应在 offscreen 下、且**不实例化 `QWebEngineView`**（只测
  `QObject` 桥 + 假 dialog）；
- shell 生命周期测试如何避免对真实 WebEngine 的依赖。

不规定的话，实施者可能写出“只在带显示的 macOS 本机能跑”的测试，无法纳入
`uv run pytest`。

**补充步骤：** Phase 3/4 增加“bridge 与 shell 单测必须
`QT_QPA_PLATFORM=offscreen` 可跑、且不得在 import 期强制创建
`QWebEngineView`”的约束。

### M5. “源码对产物”校验门缺失（评审重点明确要求）

评审请求明确要求检查“source-versus-bundle verification gates”。计划 Phase 7
的验收是：“bundle 不依赖 `.venv` 或项目源码路径”“bundle 内没有
pywebview/pythonnet”“启动失败能找到 log”——但**全部是人工检查**，没有
自动 gate。尤其缺失：

- 自动断言“冻结产物中不包含 `pywebview`/`pythonnet`/`clr_loader` 模块”
  的收集期或构建后检查；
- 自动断言“产物内的 `static/app.js`/`templates/index.html` 与源码一致”
  （防止 spec 收集到旧缓存资源）；
- 自动断言“产物不含绝对路径引用 `.venv`/项目源码目录”（可用
  `pyinstaller` 的 `warn-...txt` + grep 校验）。

**补充步骤：** Phase 7 增加一个 `tests/packaging/`（或 spec 后处理脚本）
级的自动校验步骤，见第 6 节 M5 措辞。

### M6. PyInstaller 收集 PySide6/QtWebEngine 的具体 hook 策略未定

`SummerGDS.spec` 当前**完全没有** PySide6/QtWebEngine 相关收集逻辑
（仅 klayout、matplotlib、flask 等）。Phase 7 说“收集 PySide6/QtWebEngine
进程、framework、resource、locale、plugin”，但未指定用：

- `collect_all("PySide6")`（含 QtWebEngineProcess、resources、translations），
  还是
- 手动 `collect_data_files`/`collect_dynamic_libs`/`binaries` 分项。

这两种路径在 macOS `.app` framework 结构与 Windows 上行为不同；尤其
`QtWebEngineProcess` 助手进程、`Resources/icudtl.dat`、`Resources/qtwebengine_*.pak`
极易漏收，而漏收的表现正是计划风险表列的“bundle 空白或启动失败”。需指定
“以 `collect_all('PySide6')` 为基线 + 显式核对 QtWebEngineProcess 与
`icudtl.dat`/`*.pak` 存在”的步骤。

### M7. 关闭顺序的“停止接受新请求”机制未落地为步骤

启动序列第 10 步与 §6.3 要求“关闭窗口时停止接受新对话框请求”。但具体如何
实现未列为步骤：是先 `server.shutdown()`（停止新 HTTP 请求）再唤醒 pending
桥请求，还是先关桥再停 server？顺序错误会导致：shutdown 后仍有在途 worker
进入桥、或桥唤醒早于 server 停止造成新请求又进来。需在 Phase 4 给出确定的
关闭子序列作为步骤。

---

## 4. Missing or weak tests

### T1. “正常启动路径不导入 webview/pythonnet/clr”无可执行测试

Phase 5 验收写“正常启动路径不导入 `webview`、`pythonnet` 或 `clr`”，但未
指定任何自动化测试。该断言可用 `importlib`/`sys.modules` 检查或
`pyfrost`/import-trace 实现。无测试则该 gate 形同虚设。

**建议测试：** `tests/gui/test_no_pywebview_on_launch_path.py`——在
`monkeypatch` 屏蔽 `webview`/`pythonnet`/`clr_loader` 导入的前提下，导入
`summer_gds.gui.launcher` 并调用其启动路径的纯逻辑（不真正起窗口），断言
不触发 `ImportError`、且 `sys.modules` 不含这些键。

### T2. “CLI 不导入 PySide6”无可执行测试

Phase 5 验收“CLI 不导入 PySide6”同样无测试。`summer-gds` 入口为
`summer_gds.cli:main`。需一个测试导入 `summer_gds.cli` 并断言
`PySide6` 不在 `sys.modules`。

### T3. 桥的并发/断连/异常/关闭唤醒测试仅有验收口号，无具体用例

Phase 3 验收列出“选择/取消/错误/关闭均能返回”“pending 在关闭时唤醒”
“同时请求不开多个 modal”，但计划未把这些落成具体测试名与断言。结合第 2 节
B1/B2/B3 的空白，这些测试目前无法写。需在收敛契约后补充至少：

- `test_concurrent_save_requests_*`（对应 B1 选定语义）；
- `test_worker_wait_timeout_*` 与 `test_client_disconnect_cancels_pending`
  （对应 B2）；
- `test_dialog_exception_marshaled_to_error_response`（对应 B3）；
- `test_shutdown_wakes_pending_request_returns_canceled`（关闭唤醒）；
- `test_only_one_modal_dialog_at_a_time`（互斥）。

### T4. “静态资源本地性测试”未定义

Phase 6 列“静态资源本地性测试”，但未定义断言内容。建议明确为：解析
`templates/index.html` 与 `static/app.js`，断言不存在 `http://`/`https://`
外部资源引用（CDN、远程字体/脚本/图片），与 §6.4“不允许从公网加载”对应。
当前 `app.js` 已是纯本地实现（Graphify 流 `static_app_*` 全部位于
`src/summer_gds/gui/static/app.js`），该测试可作为回归门。

### T5. macOS bundle smoke 全为人工，缺少自动产物断言

Phase 7 验收全为人工目视。至少应补充自动部分：构建后用脚本扫描
`dist/SummerGDS`（或 `dist/SummerGDS.app`）：

- 不含 `pywebview`/`pythonnet`/`clr_loader`；
- 含 `QtWebEngineProcess`、`icudtl.dat`、`qtwebengine_resources*.pak`；
- 不含指向 `.venv`/`$PROJECT_ROOT` 的绝对路径字符串。

这与 M5 配套。没有它，“bundle 内没有 pywebview/pythonnet”这条验收无法在
CI 守住。

### T6. “既有 84 项测试”基线数字含糊

Phase 5 验收“既有 84 项测试不回退”。实际仓库 `def test_` 函数数为 68
（`grep -rc` 统计：`tests/app/*` 23、`tests/gui/*` 30、`tests/schema/*` 10、
`tests/geometry/*` 2、`tests/writer/*` 1、`tests/visual/*` 2），但因
`test_base_pipeline.py`（`@pytest.mark.parametrize`，32 例）与
`test_full_pipeline_artifacts.py`（`VISUAL_CASES`、`INVALID_CASES`）的参数
化展开，**收集到的 item 数会大于 68**。84 可能是收集 item 数，但计划未说明
口径。Phase 1“记录当前 pytest 基线”应明确记录“收集 item 数 = N”，避免
实施者用不同口径自我证明“未回退”。

---

## 5. Repository / doc inconsistencies

### I1. 存在两个 `SummerGDS.spec`，计划只引用一个

仓库根有 `SummerGDS.spec`（已跟踪，4805 字节），`tests/SummerGDS.spec`
（据 git status 为未跟踪，4574 字节）。计划 §13 与 §15 只提及
`SummerGDS.spec`。需明确哪个是权威；若 `tests/SummerGDS.spec` 是历史副本，
应在 Phase 1 删除或说明关系，否则 Phase 7 “更新 spec”可能改错文件。

### I2. `server.py` 的 `close_session` teardown 实际永不触发

`server.py:130-133` 的 `close_session` 仅在
`app.config["SUMMER_GDS_CLOSE_ON_TEARDOWN"]` 为真时关闭 session，但全仓库
无任何位置设置该配置项（`grep` 验证）。因此 session 关闭完全依赖
`launcher.py:104` 的 `finally: session.close()`。计划启动序列第 10 步
“清理 session”应注明这一事实，并确保 Qt shell（`qt_shell.py`）的关闭路径
**显式调用** `session.close()`，否则在 Qt 路径下可能复刻一个“teardown 不会
关 session”的隐患。这是从 pywebview 路径继承的既有行为，计划未点名。

### I3. v1 的对话框模式与 v2 桥不同，易被误作前例

`summer_gds_v1/web_gui/qt_mainwindow.py:137-233` 的 GDS 保存走的是
**WebEngine `downloadRequested`** 信号，`QFileDialog` 在 GUI 线程直接打开
——这是浏览器发起下载、GUI 线程原生处理的模式，**不存在跨线程桥**。而 v2
的文件选择由前端调用 Flask API `/api/file/choose-save` / `/api/yaml/open`，
在 Flask worker 线程进入 `GuiSession`，必须跨线程到 GUI 线程。计划 §2.3
正确地把 v1 复用范围限定为“QtWebEngine 承载本地 Web UI 的桌面壳模式”，但
未明确警告“v1 不提供对话框桥前例”。建议补一句，避免实施者照抄 v1 的
`QFileDialog` 直调而忽略桥。

### I4. Phase 2 验收与 Phase 1“测试全绿”冲突（同 M3）

Phase 1 要求“当前测试保持全绿”；Phase 2 移动 `start_loopback_server` 会使
`test_launcher.py` 立即红，除非同阶段更新 import。Phase 2 验收未列此项，
形成阶段间不一致。已在 M3 提出修正。

### I5. 图谱新鲜度提示未在计划中作为 Phase 1 检查项

`.graphify/GRAPH_REPORT.md` 注明“Built from Git commit `dc4d0dd`”，并要求
“Compare this hash to `git rev-parse HEAD` before trusting freshness-sensitive
graph output”。计划 Phase 0/1 让评审者读图谱，但未把“核对图谱 commit 与
HEAD 一致”列为 Phase 1 基线动作。当前 HEAD 正是 `dc4d0dd`（见 git log），
所以本次评审图谱是新鲜的；但应作为流程固化，避免后续基于陈旧图谱做决策。

### I6. `flows.json` 印证契约但未在计划中引用为证据

`.graphify/flows.json` 中
`flow:gui_service_guisession_choose_save_path`、
`flow:gui_service_guisession_open_yaml`、`flow:..._save_yaml`、
`flow:..._export_gds` 全部位于 `src/summer_gds/gui/service.py` 且入口即
`file_dialog.choose_*`——这正面支撑了“桥是协议 drop-in、业务层不变”的
可行性。计划未引用这些 flow 作为证据。非阻塞，但建议在 §6.3 引用以增强
可追溯性。

---

## 6. Proposed exact wording / acceptance criteria for required fixes

以下措辞可直接并入计划相应章节，用于消除第 2、3 节的阻塞性空白。

### B1 — 并发请求契约（建议并入 §6.3，作为新增小节“并发与排队契约”）

> **并发请求契约（唯一实现）：** 桥采用“单飞（single-flight）互斥”语义。
> 同一时刻至多一个对话框请求进入 GUI 线程。第二个并发请求**立即**返回
> `{"ok": false, "canceled": true, "errors": []}`，且 `errors` 含一个
> `code="dialog_busy"` 的 issue，**不排队、不阻塞、不打开第二个对话框**。
> 选择“立即 busy 返回”而非排队，是为了避免一个 worker 持锁等待另一个
> worker 造成的死锁面，并与前端 120s 超时（`FILE_DIALOG_TIMEOUT_MS`）解耦。
> 该语义必须有对应测试 `test_concurrent_save_requests_return_dialog_busy`。

### B2 — Worker 等待超时与客户端断连（建议并入 §6.3 与 Phase 3 验收）

> **等待与取消契约：**
> 1. Worker 等待 GUI 完成设硬超时 `DIALOG_WAIT_TIMEOUT_SECONDS = 100`
>    （小于前端 120s 超时，留 20s 余量）。超时后请求返回
>    `{"ok": false, "canceled": true, "errors": [issue("dialog_timeout", ...)]}`，
>    且桥标记该 pending request 为已取消；若用户随后在对话框中确认，GUI 线程
>    丢弃结果，不回写已超时的响应。
> 2. 当检测到客户端断连（Flask request 级 `request.environ` 流关闭或
>    `werkzeug` 关闭信号）时，pending 请求被取消，GUI 线程关闭对话框（若已
>    打开），worker 不再阻塞。
> 3. 任何未成功回写客户端的 `path_token` 必须在请求结束时立即从
>    `path_tokens` 删除，不得等待 30 分钟 TTL。
> 4. 关闭窗口时，所有 pending 请求被唤醒并返回
>    `{"ok": false, "canceled": true, "errors": []}`。
>
> 对应测试：`test_worker_wait_timeout_returns_canceled`、
> `test_client_disconnect_cancels_pending`、
> `test_shutdown_wakes_pending_request_returns_canceled`。

### B3 — 跨线程异常归并（建议并入 §6.3）

> **异常归并：** GUI 线程在执行 `QFileDialog` 期间捕获一切异常，经结果通道
> 以 `{"ok": false, "canceled": false, "errors": [issue("dialog_error",
> "$.dialog", <脱敏 message>)]}` 回传 worker；Flask 路由原样 `jsonify` 该
> 结构，HTTP 200。**不得将异常伪装为 `canceled`。** `<脱敏 message>` 不得
> 包含用户文件内容或完整路径 token（遵循 §10 日志脱敏规则）。对应测试：
> `test_dialog_exception_marshaled_to_error_response`。

### B4 — Profile 选型（建议修订 §6.4 那一条）

> 将“使用独立或 off-the-record profile”改为：**“使用 off-the-record
> `QWebEngineProfile`，不持久化 cookie/cache/设置；不创建持久 profile
> 目录。”** 若未来确需持久化（例如记住窗口几何），须另起一项经评审的变更，
> 不得在此隐式引入。

### M2 — 依赖声明（建议并入 Phase 5 动作）

> 在 `pyproject.toml` 的 `dependencies` 中：移除 `pywebview>=5.0`，新增
> `PySide6>=6.8,<7`（含 `PySide6-Addons`，提供 QtWebEngine）。`pywebview`
> 仅在迁移分支短期保留时放入 `[dependency-groups].dev` 并加注释“迁移门槛
> 通过后删除”。`uv.lock` 同步更新。

### M5/T5 — 源码对产物校验门（建议作为 Phase 7 新增自动验收）

> **新增 `tests/packaging/test_bundle_contents.py`（构建后运行，非默认
> pytest）：** 对 `dist/SummerGDS`（macOS 为 `dist/SummerGDS.app`）执行：
> 1. 递归扫描 `.pyc`/模块名，断言不含 `pywebview`、`pythonnet`、
>    `clr_loader`；
> 2. 断言存在 `QtWebEngineProcess`（可执行）、`icudtl.dat`、
>    `qtwebengine_resources.pak` 系列文件；
> 3. 用 `strings`/文本扫描断言产物内不含 `.venv`、`/Users/`、
>    `Summer-GDS/src` 等开发机绝对路径；
> 4. 断言 `dist/.../summer_gds/gui/static/app.js` 与
>    `src/summer_gds/gui/static/app.js` 字节一致（源码对产物一致性）。
> 该测试由 Phase 7 的打包 smoke 脚本调用，失败即阻塞发布。

### M6 — PyInstaller 收集策略（建议并入 Phase 7 动作）

> `SummerGDS.spec` 的 `datas`/`binaries`/`hiddenimports` 增加：
> `from PyInstaller.utils.hooks import collect_all;`
> `d, b, h = collect_all("PySide6"); datas += d; binaries += b;
> hiddenimports += h`。并在构建后用 M5/T5 的断言核对 QtWebEngineProcess 与
> `icudtl.dat`/`*.pak` 实际进入产物。不得仅依赖手动 `collect_data_files`。

### I1 — spec 权威性（建议并入 Phase 1）

> Phase 1 增加：确认仓库根 `SummerGDS.spec` 为唯一权威 spec；若
> `tests/SummerGDS.spec` 为历史副本，予以删除或在计划中说明其用途，避免
> Phase 7 改错文件。

---

## 7. Final ordered implementation checklist

按依赖顺序排列；每项标注所属阶段与对应上文编号，便于实施者逐条关闭。

1. **[Phase 1]** 核对 `.graphify/GRAPH_REPORT.md` 的构建 commit
   `dc4d0dd` 与 `git rev-parse HEAD` 一致；记录 pytest 收集 item 基线数
   （明确口径为“collected items”，非“test functions”）。→ 解决 T6 / I5。
2. **[Phase 1]** 确认 `SummerGDS.spec` 为权威 spec；处理
   `tests/SummerGDS.spec` 副本。→ 解决 I1。
3. **[Phase 2]** 将 `LoopbackServerHandle` 与 `start_loopback_server()`
   迁入 `runtime.py`，保持 host/随机端口/threaded/stop·join·server_close
   语义；`runtime.py` 不得导入 PySide6/pywebview/matplotlib。
4. **[Phase 2]** 同步更新 `tests/gui/test_launcher.py` 的 import
   （`LoopbackServerHandle`/`start_loopback_server` 改自 `runtime`），
   并将该更新列入 Phase 2 验收 gate。→ 解决 M3 / I4。
5. **[Phase 2]** 确定 matplotlib 预热代码（现 `launcher.py:15-19`）的归属
   模块，保留“首批 matplotlib 导入前执行”约束。→ 解决 M1。
6. **[Phase 3]** 实现 `qt_dialog.py`，按第 6 节 B1/B2/B3 的**确定契约**
   实现单飞互斥、100s worker 超时、客户端断连取消、跨线程异常归并、关闭
   唤醒；实现 `SaveFileDialog` protocol（`choose_open_path`/
   `choose_save_path`）保持 `GuiSession` 不变。
7. **[Phase 3]** 补充桥测试：`test_concurrent_save_requests_return_dialog_busy`、
   `test_worker_wait_timeout_returns_canceled`、
   `test_client_disconnect_cancels_pending`、
   `test_dialog_exception_marshaled_to_error_response`、
   `test_shutdown_wakes_pending_request_returns_canceled`、
   `test_only_one_modal_dialog_at_a_time`。所有桥测试须
   `QT_QPA_PLATFORM=offscreen` 可跑且不在 import 期创建 `QWebEngineView`。
   → 解决 T3 / M4。
8. **[Phase 4]** 实现 `qt_shell.py`：`QApplication`/`QMainWindow`/
   `QWebEngineView` + off-the-record profile；导航/权限/新窗口/下载限制；
   load failure / render crash / 后端中断诊断日志；窗口关闭触发确定子序列
   “先停接受新请求 → 唤醒 pending 桥 → shutdown Flask → join →
   `session.close()` → 退出事件循环”。`qt_shell` 显式调用 `session.close()`
   （不依赖 `server.py` teardown）。→ 解决 I2 / M7。
9. **[Phase 4]** 补充 shell 生命周期测试（offscreen、不实例化 WebEngine 的
   纯生命周期部分）与静态资源本地性测试（断言 `index.html`/`app.js` 无
   外部 `http(s)` 引用）。→ 解决 T4。
10. **[Phase 5]** `pyproject.toml`：移除 `pywebview`，新增 `PySide6>=6.8,<7`；
    `pywebview` 暂入 dev 组并注释待删；同步 `uv.lock`。→ 解决 M2。
11. **[Phase 5]** `launcher.py` 改为启动 Qt shell；保持
    `summer-gds-gui = summer_gds.gui.launcher:main`。
12. **[Phase 5]** 新增 `tests/gui/test_no_pywebview_on_launch_path.py`
    （屏蔽 `webview`/`pythonnet`/`clr_loader` 后走启动纯逻辑，断言
    `sys.modules` 不含这些键）与 `tests/cli/test_cli_no_pyside.py`
    （导入 `summer_gds.cli` 断言 `PySide6` 不在 `sys.modules`）。
    → 解决 T1 / T2。
13. **[Phase 5]** Qt source-run + 全量 pytest（含新增 Qt 专项）通过前，
    保留旧 pywebview 文件；门槛全过后删除 `desktop.py`、pywebview 依赖与
    pythonnet/clr 诊断说明。不增加双壳 CLI 参数。
14. **[Phase 6]** macOS 本机：`uv sync` → `uv run pytest -q` → 真实窗口
    smoke（创建 base/via/rings、SVG 预览、保存/打开 YAML、导出 GDS、各取消
    一次、关闭、检查无残留 server/thread/temp session）。
15. **[Phase 7]** 更新 `SummerGDS.spec`：用 `collect_all("PySide6")` 收集
    PySide6/QtWebEngine 进程/framework/resource/locale/plugin + GUI 静态
    资源；构建 windowed onedir。→ 解决 M6。
16. **[Phase 7]** 从 `dist/` 运行（非源码环境）；新增
    `tests/packaging/test_bundle_contents.py` 自动断言：无
    pywebview/pythonnet/clr_loader、有 QtWebEngineProcess+icudtl.dat+*.pak、
    无开发机绝对路径、`app.js` 与源码字节一致。→ 解决 M5 / T5。
17. **[Phase 7]** `document-diagrams` freshness check 与 pytest 同时通过。
18. **[Phase 8]** Windows ARM 虚拟机：重建构建环境 → pytest → Windows onedir
    → 核对 QtWebEngineProcess 与依赖文件 → 启动检查 loopback/日志/退出清理；
    用户目视验收窗口、字体、modal 前置、中文路径、SVG 预览、GDS 导出、关闭
    无残留。记录实际架构与 emulation 类型，不标记原生 x64 完成。
19. **[Phase 9]** 干净原生 Windows x64：无 Python/.NET/开发工具、普通用户、
    离线、中英文路径、安装/升级/卸载、GUI 工作流、Defender/SmartScreen、
    VC++ Runtime 由安装器处理、签名策略确定。通过后方可声明 Windows x64
    正式兼容。
20. **[Phase 10]** 选安装器技术、放入正常安装目录、创建入口与卸载、检测/部署
    VC++ Runtime、更新 `README.md`/`docs/frontend/*`/测试策略、删除 pywebview
    用户文档、记录 Qt/PySide6 与第三方 notice。

---

### 评审小结

方向正确、边界守得住、阶段与文件映射清晰，依赖方向经图谱与代码双向核对干净。
主要风险集中在**文件对话框线程桥的并发/超时/断连/异常契约**（B1–B3）与
**打包产物的自动校验门**（M5/M6/T5）。按第 6 节措辞收敛契约、按第 7 节
清单补齐步骤与测试后，计划可进入实施。在上述阻塞项关闭前，不建议判为
`READY`。
