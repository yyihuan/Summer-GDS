# DS4P 第二轮独立评审：Qt 桌面壳迁移计划 v1.1 闭合审查

评审人：DS4P（独立架构与安全评审）
评审日期：2026-07-29
评审对象：[qt-desktop-shell-migration-plan.md v1.1](../planning/qt-desktop-shell-migration-plan.md)
评审分支：`codex/qt-desktop-shell`
评审基线提交：`dc4d0dd`
输入材料：

- [迁移计划 v1.1](../planning/qt-desktop-shell-migration-plan.md)
- [第一轮意见处置](../reviews/qt-desktop-shell-round1-disposition.md)
- [DS4P 第一轮评审](../reviews/qt-desktop-shell-ds4p-review.md)
- [GLM 第一轮评审](../reviews/qt-desktop-shell-glm-review.md)
- 全部四份 `.mmd` 源图和 `.svg` 文件（`docs/diagrams/`）
- Graphify 图谱报告和 flows（`.graphify/GRAPH_REPORT.md`、`.graphify/flows.json`）
- 当前源码：`launcher.py`、`desktop.py`、`server.py`、`service.py`、`app.js`
- `pyproject.toml`、`uv.lock`、`SummerGDS.spec`
- `tests/gui/` 全部测试文件

---

## 1. 总体裁决

**裁决：`APPROVE`**

计划 v1.1 逐项关闭了第一轮评审产生的全部 4 个阻塞性问题和 8 个高优先级发现，
并收敛了 GLM 评审指出的 5 个阻塞性歧义。被调整或不采用的建议均给出具体、
可检验的理由，未留下新的正确性空白。

以下关键契约对实施者而言是确定的，不存在两种不同但都合理的实现选择：

- PyInstaller 打包策略（内置 hooks + 清单门 + 最小补项路径）。
- KLayout/Qt 冲突面处理（删除过度收集 + 逐平台依赖分析 + 风险待排除）。
- dialog 单飞、100 秒超时、原子终态、晚结果丢弃。
- `GuiSession.path_tokens` 加锁策略和并发契约。
- shutdown 确定顺序、`RequestGate` worker drain、`aboutToQuit` 仅作兜底。
- WebEngine 安全配置、JS 诊断、renderer crash 策略（含不自动 reload 的明确理由）。
- 三类平台证据边界（macOS 本机 / Windows ARM x64 emulation / 原生 x64）。

一个实施者按计划实现将得出行为确定的系统；不存在无测试可判对错的多解分支。

---

## 2. 第一轮 Blocker 闭合矩阵

### B1 — PyInstaller spec 缺失 PySide6/QtWebEngine 打包策略

**状态：CLOSED**

计划 v1.1 §7.2 给出完整策略：

1. 使用锁定版 PyInstaller 6.21.0 的内置 PySide6 hooks 作为默认收集机制
   (`SummerGDS.spec:19-21` 已使用 `collect_data_files`、`collect_submodules`、
   `collect_dynamic_libs` 范式——该模式可扩展到 `from PyInstaller.utils.hooks
   import collect_all`)。
2. `qt_shell.py` 必须直接 import 实际使用的 Qt 模块
   (`PySide6.QtCore`/`QtGui`/`QtWidgets`/`QtWebEngineCore`/`QtWebEngineWidgets`)，
   不依赖隐式传递。
3. 不默认调用 `collect_all("PySide6")`；仅在内置 hooks 被证明确有漏项时，以
   最小、带注释、有失败证据和自动断言的补项修正 (§7.2 项 3)。
4. 每个平台有具体产物清单（platform plugin / WebEngine helper / Chromium
   resources / locales / Qt libraries）作为验证目标 (§7.2 表格)。
5. §7.4 的 `verify_desktop_bundle.py` 提供 9 项可执行自动检查，覆盖 plugin、
   helper、resources、locales、模块排除、静态 hash、动态库、迁移目录启动和
   业务 probe。

处置 D01 明确拒绝 `collect_all("PySide6")` 作为默认策略，理由（体积和冲突面
扩大）成立。内置 hooks + 清单门 + 最小补项路径构成可审计的闭环：遗漏会被
清单门发现，修复会被追迹到具体失败证据。

**证据**：计划 §7.2、§7.4；处置 D01。

---

### B2 — GuiSession.path_tokens 字典无线程安全保护

**状态：CLOSED**

计划 v1.1 §6.4 精确规定：

- 新增一个普通 `threading.Lock`（不用 `RLock`，因为锁内 helper 不回调公共方法）。
- `choose_save_path()` 在进入 dialog 前加锁清理过期 token，成功选择后再次加锁
  清理并插入 token。
- `_resolve_path_token()` 在锁内执行查找、过期删除和 kind 校验。
- `close()` 在锁内清空 token，再清理 session 目录。
- token 在 TTL 内可复用，支持 force 重试路径。
- preview 使用单调递增 request ID 生成不同临时文件，并发 preview 测试确保不同
  ID 不互相删除。
- shutdown 先阻止新 API / 取消 dialog，server 请求收敛后调用 `session.close()`，
  避免目录清理与在途操作竞争。

处置 D02 接受此方案。关键设计是 "dialog 在锁外执行" —— 这意味着长时间阻塞的
dialog 不会持有 `path_tokens` 锁，其他 token resolve 调用不会被阻塞。

**当前代码证据**：`service.py:49`（`path_tokens: dict` 无锁）、`service.py:125`
（无锁写入）、`service.py:212`（无锁条件删除）、`service.py:218-222`
（`_purge_expired_tokens` 从未被调用）。所有这些问题都在计划 v1.1 中得到纠正。

**证据**：计划 §6.4；处置 D02。

---

### B3 — KLayout 原生库与 PySide6 Qt 库的符号冲突风险未评估

**状态：CLOSED**

计划 v1.1 §7.3 规定：

1. 删除 `collect_submodules("klayout")`（当前 `SummerGDS.spec:91-94` 有此调用）。
2. 删除当前 spec 中未实际触发的 hiddenimports（`klayout.lay`、`klayout.rdb`、
   `klayout.lib`、`klayout.pex` —— 当前 `SummerGDS.spec:66-71`）。
3. 生产源码只 `import pya`，本机 trace 触发 `klayout.db`、`klayout.dbcore`、
   `klayout.pya`、`klayout.pyacore`、`klayout.tl`、`klayout.tlcore` ——
   不需要 GUI 相关模块。
4. 用 `otool -L`（macOS）/ `dumpbin /dependents`（Windows）记录 KLayout 和
   QtWebEngine 的二进制依赖。
5. 明确状态："产物不得出现由 KLayout 额外带入的另一套 Qt。当前源码审计没有
   证明存在冲突，因此风险状态是'需逐平台排除'，不是'已确认冲突'。"

处置 D03 接受此策略。这正确地将冲突处理为"待验证风险"而非"既定事实"，且
提供了逐平台验证的具体方法。

**证据**：计划 §7.3；处置 D03。

---

### B4 — 文件对话框桥无超时机制，关闭路径存在永久阻塞风险

**状态：CLOSED**

计划 v1.1 §6.3.3 和 §6.5 完整定义：

- 硬超时 `DIALOG_WAIT_TIMEOUT_SECONDS = 100`（小于前端 120 秒，留 20 秒余量）。
- 原子终态：request 只能从 pending 转为 selected / canceled / failed /
  timed_out / closing 之一，任何终态不能被第二次完成覆盖。
- worker 超时后将 request 标为 `timed_out`，向 GUI thread 发 cancel，返回
  `dialog_timeout`。GUI late result 必须被丢弃。
- active gate 只在 GUI thread 完成或关闭原 dialog 后才释放；worker 超时本身
  不释放 gate（防止第二 dialog 与旧 modal 并存）。
- shutdown §6.5 步骤 3：bridge 立即拒绝新 dialog，关闭 active QFileDialog，
  唤醒 pending worker。
- §6.5 步骤 8：`aboutToQuit` 仅作兜底，不实现第二套清理。

处置 D04（超时 100 秒）、D06（客户端断连不作为正确性依赖）、D07（晚结果丢弃）
逐项支持此设计。

**关键决策**：对比 DS4P 建议的 30 秒和 GLM 建议的 100 秒，计划选用 100 秒，
理由为"30 秒会把正常人工选路误判为失败"。这是合理的工程判断，且有前端 120
秒作为上限和 20 秒余量缓冲。

**证据**：计划 §6.3.3、§6.5；处置 D04、D06、D07。

---

## 3. 第一轮高优先级发现闭合矩阵

### H1 — LGPL 许可证合规策略缺失

**状态：CLOSED**

计划 §7.5 将许可证门提升到 Phase 1（原为 Phase 10），包括：license inventory、
`LICENSES/` / `THIRD_PARTY_NOTICES` 文件、适用替换/重链接/源码获取检查表、
QtWebEngine/Chromium notices 收集、项目负责人确认商业许可或开源合规。处置 D18
明确接受并前移。

**证据**：计划 §7.5；处置 D18。

---

### H2 — QWebEngineView 渲染进程崩溃检测与恢复策略缺失

**状态：CLOSED**

计划 §6.6 精确定义：

- 监听 `renderProcessTerminated(status, exit_code)`。
- 正常 shutdown 期间忽略；运行期间的 abnormal/crashed/killed 写日志、取消
  pending dialog、显示原生错误并退出。
- 首版不自动 reload。理由是自动 reload 可能无提示丢失未保存的浏览器状态并形成
  crash loop，必须等有状态恢复设计后另案评审。
- 首版不引入 QWebChannel heartbeat。

处置 D10 调整后接受（不自动 reload）。这个决策有明确的失败场景分析，不是
简单忽略。

**证据**：计划 §6.6；处置 D10。

---

### H3 — Windows ARM QtWebEngine 可用性未确认

**状态：CLOSED**

计划 §5.2 出具了 2026-07-29 的 PyPI wheel 证据：

- PySide6 6.11.1：Windows AMD64 和 Windows ARM64。
- PyInstaller 6.21.0：Windows AMD64 和 Windows ARM64。
- KLayout 0.30.8：Windows AMD64/Win32，没有 Windows ARM64。

因此完整交集只有 AMD64。Parallels ARM VM 阶段固定为 "AMD64 Python 3.13 →
AMD64 wheels → AMD64 SummerGDS onedir → x64 emulation on ARM host"。
不构建 Win32，不宣称 native ARM。正式支持由原生 Windows 11 x64 clean-machine
gate 决定（Phase 9）。

处置 D14 收窄后接受。这与 DS4P 第一轮的担心一致——"Phase 8 测试的是 x64
emulation 而非原生 ARM"——且计划现在明确标注了这一点。

**证据**：计划 §5.2；处置 D14。

---

### H4 — 无前端 JavaScript 静默失败检测机制

**状态：CLOSED**

计划 §6.6 定义了三层可见性：

1. 自定义 `QWebEnginePage.javaScriptConsoleMessage()`：warning/error 转发到
   Python log，info 只在开发 debug 级别记录，单条截断并脱敏。
2. `loadFinished(true)` 后用 `runJavaScript` 检查 `#app`、`#workspace` 和
   显式 app-ready marker `window.SUMMER_GDS_APP_READY = true`。
3. `loadFinished(false)` 或 DOM 检查失败显示原生致命错误并退出。

处置 D11 接受核心项（不引入 QWebChannel heartbeat）。

**需实施注意**：当前 `app.js` 未设置 `window.SUMMER_GDS_APP_READY`，计划 §6.1
和 §14 将 `app.js` 列为修改项（"仅增加内部 app-ready marker"）。这是明确的。

**证据**：计划 §6.6；处置 D11。

---

### H5 — Qt 平台插件部署策略未细化

**状态：CLOSED**

计划 §7.2 给出平台特定清单：

| 类别 | macOS | Windows AMD64 |
| --- | --- | --- |
| platform plugin | `libqcocoa.dylib` | `qwindows.dll` |
| WebEngine helper | `Helpers/.../QtWebEngineProcess.app` | `QtWebEngineProcess.exe` |
| Chromium resources | `icudtl.dat`、`qtwebengine_resources*.pak` | 同左 |
| locales | `qtwebengine_locales` 含 `en-US`/`zh-CN` | 同左 |

路径以 PyInstaller 实际布局为准，不通过设置用户环境变量修复错误 bundle。
`verify_desktop_bundle.py`（§7.4 项 2）自动断言这些文件存在且 helper 可执行。

处置 D01 将此纳入总体打包策略。

**证据**：计划 §7.2、§7.4；处置 D01。

---

### H6 — 生产环境 Flask Werkzeug debugger 风险未设防

**状态：CLOSED**

计划 §6.7 规定：

- `create_app()` 显式设置 `DEBUG=False`、`TESTING=False`。
- 生产启动不用 `app.run()`、不用 reloader、不套 Werkzeug debugger /
  `DebuggedApplication`。
- 打包测试断言这些配置和 server 创建路径。

处置 D12 接受。这直接回应了第一轮指出的"`create_app` 无 debug 强制关闭逻辑"
（`server.py:20-29`）。

**证据**：计划 §6.7；处置 D12。

---

### H7 — 冻结包 smoke 测试缺乏自动化检查

**状态：CLOSED**

计划 §7.4 的 `verify_desktop_bundle.py`（或等价脚本）定义了 9 项自动检查：

1. 读取 PyInstaller Analysis/TOC/warning，失败于 missing required module。
2. 断言所需 Qt platform plugin、WebEngine helper、resources、locales 存在且
   helper 可执行。
3. 断言产物不含 `webview`、`pythonnet`、`clr_loader`、`clr`。
4. 对 index.html、app.js、style.css、favicon 做 SHA-256，断言与源码一致。
5. 解析动态库依赖，断言没有引用项目 `.venv`、源码目录或构建机非系统绝对路径。
6. 复制完整 bundle 到仓库外、名称含空格/中文的临时目录。
7. 清除开发环境变量，从新目录启动。
8. 等待内部 app-ready marker / ready log（而非仅检查进程存活）。
9. 执行固定 YAML → SVG → GDS probe，退出后断言端口和 session 临时目录已清理。

这些检查覆盖了 M5/T5/GLM M5 的所有关注点。处置 D17 调整后接受，明确不对全部
二进制做脆弱的全局 `/Users/` 断言。

**证据**：计划 §7.4；处置 D17。

---

### H8 — 并发 API 请求安全性未评估

**状态：CLOSED**

此问题已分解为多个子项，均获解决：

- `path_tokens` 竞态 → §6.4 Lock 保护（处置 D02）。
- dialog 并发 → §6.3.2 single-flight，立即返回 `dialog_busy`（处置 D05）。
- preview 并发 → §6.4 单调递增 request ID，并发 preview 测试。
- session 清理竞态 → §6.5 shutdown gate，收敛后 close（处置 D02）。

**证据**：计划 §6.3.2、§6.4、§6.5；处置 D02、D05。

---

## 4. GLM 阻塞性歧义闭合矩阵

### GLM B1 — 并发文件对话框请求语义未定义

**状态：CLOSED**

计划 §6.3.2 定义 single-flight：第二个请求原子地立即返回 `dialog_busy`，
不排队、不等待、不打开第二个 modal。处置 D05 明确 `canceled=false`（busy
不是用户取消）。计划 Phase 3 列出对应测试 `test_second_dialog_returns_busy_without_queueing`。

**证据**：计划 §6.3.2；处置 D05。

---

### GLM B2 — Worker 等待超时与客户端断连未处理

**状态：CLOSED**

计划 §6.3.3 定义 100 秒硬超时、原子终态、late result discard、gate release
机制。§6.3.3 明确"同步 Flask/Werkzeug 的客户端断连检测不是 correctness 依赖。
若未来有可靠信号，可以提前触发同一 cancel 状态机，但不能形成另一套语义。"
处置 D06 对此有详细论证。Phase 3 列出超时和晚结果丢弃的对应测试。

**证据**：计划 §6.3.3；处置 D06。

---

### GLM B3 — GUI 线程异常如何归并回 Flask worker 线程

**状态：CLOSED**

计划 §6.3.1 定义 `DialogFailure(code, safe_message)` 异常类，`GuiSession`
捕获并映射为现有 issue response。响应语义表明确列出 `dialog_error` 场景：
HTTP 200、`ok=false`、`canceled=false`、error code `dialog_error`。处置 D08
明确"不把 Qt 类型带入服务层"、`dialog_error` 不伪装为 `canceled`。Phase 3
列出对应测试 `test_dialog_exception_maps_to_dialog_error`。

**证据**：计划 §6.3.1（响应语义表）；处置 D08。

---

### GLM B4 — QWebEngineProfile 二选一未定

**状态：CLOSED**

计划 §6.6 明确选择 off-the-record："使用 `QWebEngineProfile(parent)` 无
storage name 的独立 off-the-record profile"、"不创建持久 cookie/cache/profile
目录"。处置 D09 接受此方案。GLM 建议的措辞已实质采纳。

**证据**：计划 §6.6；处置 D09。

---

### GLM B5 — 桥的"单请求互斥"与 GUI 线程被其他 modal 阻塞

**状态：CLOSED**

§6.3.3 的 100 秒超时同样覆盖此场景——若 GUI 线程因任何原因不处理 queued
signal，worker 在 100 秒后超时并返回 `dialog_timeout`。这与 B2 的同源问题
通过同一超时契约解决。GLM 建议合并到 B2 的超时契约中一并解决——计划已执行。

**证据**：计划 §6.3.3。

---

## 5. 新的阻塞性发现

**None.**

经逐项闭合审查，未发现新的 blocker。以下关注点在详细检查后确认为非阻塞。

---

## 6. 被拒绝/调整决策的逐项审查

### D01 — 冻结打包策略（拒绝 blanket `collect_all("PySide6")`）

**审查结论：SAFE**

理由成立。PySide6 的 `collect_all` 会带入未使用的 Qt 模块（QML、Multimedia、
Sensors 等）、所有翻译文件和插件，显著增加产物体积和潜在冲突面。计划选择的
策略——锁定版本 PyInstaller 内置 hooks + 具体 import 清单 + 产物清单门 +
最小补项路径——在工程上是正确折衷。清单门的 9 项检查足以在任何漏项抵达用户
前捕获它。

---

### D04 — Dialog 超时采用 100 秒（拒绝 DS4P 建议的 30 秒）

**审查结论：SAFE**

100 秒和 30 秒都是合理选择。计划的理由（30 秒误判正常选路）成立，且 100 秒
在前端 120 秒内留有 20 秒余量。值得注意：GLM 同样建议 100 秒。这构成两份
独立评审的共识。

---

### D06 — HTTP 客户端断连不作为正确性依赖

**审查结论：SAFE**

这是关键的正确性决策。同步 Flask/Werkzeug 确实没有可靠的跨平台请求断连取消
信号（Werkzeug 的 `stream_close` 在 Windows 上行为不同）。依靠 100 秒硬超时
而非脆弱的平台信号是防御性的正确选择。计划同时保留未来优化路径（"若未来有
可靠信号，可以提前触发同一 cancel 状态机"），但不让另一种语义混入。这体现了
良好的协议设计纪律。

---

### D07 — Late result 与 token（计划调整 GLM 建议的机制）

**审查结论：SAFE**

GLM 建议 "任何未成功回写客户端的 path_token 必须在请求结束时立即从
path_tokens 删除"。计划将其调整为：token 只有在 bridge 成功返回路径后由
`GuiSession` 创建——如果 bridge 超时或失败，token 根本不会被创建。这比
"创建后删除"更简洁、更少竞态面。两类实现都正确，计划的选择更优。

---

### D10 — Renderer crash 不自动 reload

**审查结论：SAFE**

DS4P O7 建议最多 3 次自动 reload，exponential backoff。计划拒绝自动 reload，
理由为：（1）可能无提示丢失未保存的浏览器状态；（2）可能形成 crash loop；
（3）需要状态恢复设计后另案评审。考虑到本应用有真实的用户编辑状态（未保存
YAML 修改），无声丢失这些状态比显示错误消息更差。不自动 reload 是正确的
首版选择。

---

### D13 — 依赖精确锁定（拒绝宽泛版本范围）

**审查结论：SAFE**

计划锁定 `PySide6==6.11.1`、`PyInstaller==6.21.0`、`KLayout==0.30.8`，由
`uv.lock` 固化传递依赖。DS4P 第一轮 M3 要求锁定版本，GLM M2 倾向
`>=6.8,<7`。计划选择精确锁定，并在 §5.1 规定"Phase 1 dependency probe 失败
时，应记录具体 wheel/import/build 证据后修改精确版本并重跑全部门槛，不能悄悄
放宽为大版本范围"。这是最优策略——精确记录一个可行的版本组合，而非让范围
漂移。

---

### D14 — Windows ARM 定位收窄

**审查结论：SAFE**

由于 KLayout 缺少 Windows ARM64 wheel，完整交集只有 AMD64。计划将 ARM 阶段
限定为 AMD64 on x64 emulation 且不宣称 native ARM。§5.2 wheel 分析与 Phase 8/9
的证据标签正确区分了三类平台状态。

---

### D16 — 拒绝 `collect_all("PySide6")`

**审查结论：SAFE**（同 D01 论证）

---

### D17 — Bundle 绝对路径检查调整

**审查结论：SAFE**

DS4P 第一轮未具体要求此项。GLM M5/T5 建议对产物做 `strings | grep` 路径检查。
计划调整为使用 TOC/dynamic lib/static hash 检查代替脆弱的 `strings` 扫描。
理由是编译器元数据可能产生误报。这是合理的——`verify_desktop_bundle.py`
的项 3（TOC 层面不含 pywebview 等）、项 5（动态库依赖不引用 `.venv`）和
项 6（迁移到含空格/中文目录启动）共同提供了更强的保证。

---

### D18 — 许可证门槛前移

**审查结论：SAFE**

从 Phase 10 移至 Phase 1，符合 DS4P H1 的要求。

---

### D19 — 拒绝 headless product flag

**审查结论：SAFE**

DS4P O1 建议增加 `--headless` 用于 CI 中冻结包 smoke。计划拒绝，理由为
headless 不验证 QWebEngine 桌面壳，且会扩大对外 CLI 契约。替代方案为
内部 bundle probe（`verify_desktop_bundle.py` 第 8-9 项）+ offscreen 单测 +
真实窗口 smoke。不增加对外 CLI 参数是合理的范围克制。

---

## 7. 剩余高优先级发现

**None.**

---

## 8. 剩余中优先级发现

以下项目在 v1.1 中已解决，不是未闭合问题：

### M1 — 迁移中间阶段的 ImportError 风险

**状态：PENDING IMPLEMENTATION，非计划缺陷**

当前 `launcher.py:24` 顶层导入 `PyWebviewSaveFileDialog`。计划 §6.1 模块布局
将删除 `desktop.py`，改用 `qt_dialog.py`。Phase 5 规定"Qt source/bundle gate
通过前可在迁移分支保留旧文件供 diff；通过后删除 `desktop.py` 和生产路径
pywebview import"。这是一个实施序列问题而非计划设计问题。建议实施者先移走
顶层 import 再用新模块替换，避免中间状态 `ImportError`。

### M2 — 测试假对象与 pywebview 紧密耦合

**状态：已计划**

Phase 2 同步迁移 `test_launcher.py` 的 import，Phase 3 提供 bridge 测试专用
fake dialog factory。计划明确 bridge 测试"使用 fake dialog factory 和 Qt
event dispatch，不实例化 `QWebEngineView`，也不弹真实 modal"（§8 Phase 3）。

### M3 — Qt 版本未锁定

**状态：CLOSED**

计划 §5.1 精确锁定 `PySide6 6.11.1`。

### M4 — start_loopback_server() 缺少就绪信号

**状态：CLOSED**

计划 §6.2 步骤 7 规定"runtime 在 5 秒总时限内轮询 GET /；只有收到预期 HTML
才视为 ready"。old v1 pattern (`server.wait_ready(timeout=10.0)`) 已继承。

### M5 — 运行时内存

**状态：ACCEPTED MONITORING**

计划不设硬阈值，但 §11 规定记录 source/bundle 冷启动时间和稳定内存作为趋势
基线。处置 D20 接受此方案。

### M6 — 渲染进程崩溃的测试策略

**状态：已计划**

计划 §8 Phase 4 规定"load failure、DOM failure、renderer failure 的 handler
可通过 fake page/signal 参数测试"。

### M7 — 日志文件无轮转

**状态：CLOSED**

计划 §11 规定 `RotatingFileHandler`，1 MiB 文件、3 备份、UTF-8。处置 D20
接受。

### GLM M1 — matplotlib 预热落点

**状态：CLOSED**

计划 §6.1 和 §6.2 步骤 1 规定 matplotlib 预热留在 `launcher.py` 并在任何可能
触发 matplotlib 的应用模块 import 之前执行。`runtime.py` 不导入 matplotlib。

### GLM M2 — PySide6 依赖声明

**状态：CLOSED**

计划 §5.1 锁定 `PySide6==6.11.1`（meta wheel 同步提供 Essentials/Addons，
QtWebEngine 位于 Addons）。Phase 5 精确加入依赖。

### GLM M3 — test_launcher.py import 更新

**状态：CLOSED**

Phase 2 验收中列为独立动作"同一提交更新 `tests/gui/test_launcher.py` 的 import
和 fakes"。这直接回应 GLM 指出的 Phase 2 验收未列此项的问题。

### GLM M4 — CI/无头测试下的 QApplication 策略

**状态：CLOSED**

Phase 3 规定"bridge 测试使用 fake dialog factory 和 Qt event dispatch，不
实例化 QWebEngineView，也不弹真实 modal"。Phase 4 规定"纯 lifecycle 测试
可在 offscreen 环境、无 WebEngine 实例下运行"。这确保测试在 CI 可跑。

### GLM M5/M6 — 源码对产物校验门 / PyInstaller 收集策略

**状态：CLOSED**

已在 B1/H7 闭合中讨论。计划选择内置 hooks + 清单门而非 `collect_all`。

### GLM M7 — 关闭顺序

**状态：CLOSED**

计划 §6.5 给出 8 步确定关闭子序列，Phase 4 验收要求"正常关闭清理 server、
端口和 session；重复 close 幂等"。

---

## 9. 剩余低优先级发现

### L1 — QWebEngineProfile 策略

**状态：CLOSED** — 已选定 off-the-record（§6.6）。

### L2 — loadFinished 错误处理

**状态：CLOSED** — §6.6 规定 `loadFinished(false)` "显示原生致命错误并退出"。

### L3 — Unicode 路径测试

**状态：CLOSED** — Phase 3 明确列出"中文、emoji、空格路径 open/save/cancel"
测试。

### L4 — QApplication.quit() 调用时机

**状态：CLOSED** — §6.5 步骤 7 规定"销毁 page/profile/window，最后调用
`QApplication.quit()`"。§6.5 设置 `setQuitOnLastWindowClosed(False)` 防止
绕过 coordinator。

### L5 — v1 下载功能清理

**状态：N/A** — 计划 §3.3 明确"本迁移不迁移 v1 的 QWebEngine download
功能"。计划 §6.6 明确"不使用 WebEngine download 处理 YAML/GDS"。

---

## 10. 实施就绪检查清单

以下项目逐条验证通过（✓）或标注实施注意事项：

- [x] **B1**：PyInstaller spec 策略已确定（内置 hooks + 清单门 + 最小补项路径）。
- [x] **B2**：`GuiSession.path_tokens` 已定义 `threading.Lock` 策略和调用时机。
- [x] **B3**：KLayout 冲突面策略已确定（删除过度收集 + 逐平台依赖分析）。
- [x] **B4**：File dialog bridge 已定义超时（100s）、原子终态、晚结果丢弃和
  shutdown 取消协议。
- [x] **H1**：许可证门已前移到 Phase 1。
- [x] **H2**：`renderProcessTerminated` 策略已确定（日志 + 取消 dialog + 错误 + 退出；
  不自动 reload）。
- [x] **H3**：Windows ARM 的 PySide6 wheel 状态已查明（有 ARM64 wheel；KLayout 无；
  完整交集 AMD64）。
- [x] **H4**：JS console message → Python log 转发已纳入设计。
- [x] **H5**：Qt 平台插件收集已有平台特定清单。
- [x] **H6**：`create_app()` 将强制执行 `DEBUG=False`、`TESTING=False`。
- [x] **M3**：PySide6 版本已锁定为 6.11.1。
- [x] **M4**：`runtime.py` 启动函数包含 5 秒有界 HTTP readiness probe。
- [ ] **Phase 1 基线**：pytest 基线需重新记录 collected items 数（计划用
  "collected items" 口径）。
- [ ] **app.js 修改**：需设置 `window.SUMMER_GDS_APP_READY = true`（计划已
  列为修改项）。
- [ ] **`SummerGDS.spec` 权威性**：`tests/SummerGDS.spec` 是用户已有 untracked
  副本（4574 字节）——计划已规定不删除、不修改、不提交。
- [ ] **uv.lock**：当前不含 PySide6/PyInstaller（项目目前依赖 pywebview）——
  将在 Phase 5 添加。

---

## 11. 图谱验证摘要

Graphify 图谱基于 commit `dc4d0dd`（与当前 HEAD 一致），为迁移前代码基线：

- Community 5（launcher/desktop/pywebview hub，22 节点）是替换目标。计划 §6.1
  的新模块布局直接匹配该社区的节点替换映射。
- Community 6（GuiSession/service，39 节点）是应保持稳定的区域——计划通过
  protocol-based `SaveFileDialog` 接口保持 `GuiSession` 不变，吻合图谱隔离。
- `flows.json` 中 `gui_service_guisession_choose_save_path`、
  `gui_service_guisession_export_gds`、`gui_service_guisession_save_yaml` 等
  flow 均以 `file_dialog.choose_*` 为入口——正面支撑"桥是协议 drop-in、业务层
  不变"的可行性。
- 85 条 INFERRED 边（平均置信度 0.5）已记录为可能噪声，未用于微观决策。

图谱在实现后需要基于新 commit 重建，作为 `document-diagrams` freshness check
的一部分（Phase 7 验收项）。

---

## 12. 实施顺序建议（非阻塞）

以下建议不改变计划逻辑，仅优化实施顺序以降低风险：

1. **Phase 2 实施时优先处理 `launcher.py:24` 顶层 import**：在移除 `desktop.py`
   前，先将 `PyWebviewSaveFileDialog` 从顶层 import 改为延迟导入（如移至
   `launch_desktop()` 内部），避免中间状态 `ImportError`。
2. **Phase 3 实施时将 `_purge_expired_tokens()` 的首次调用设在
   `__post_init__` 后的首次 `choose_save_path()`**，确保迁移前遗留的过期 token
   被清理（当前代码中该方法从未被调用）。
3. **Phase 5 实施时先添加 PySide6 依赖再删除 pywebview**，避免环境在两次
   `uv sync` 之间同时缺少两套桌面壳。

---

## 13. 评审局限

本评审基于计划文本、处置文档、源码和图谱。以下项目无法从当前材料中验证：

- PySide6 6.11.1 + PyInstaller 6.21.0 内置 hooks 在 macOS x86_64 上的实际
  收集行为——这必须在 Phase 1 的 dependency probe 中验证。
- KLayout 0.30.8 二进制是否链接另一套 Qt —— 这必须在 Phase 7 的 `otool -L`
  分析中验证。
- Windows ARM x64 emulation 下 QtWebEngineProcess 是否稳定 —— 这必须在
  Phase 8 验证。

计划已将以上设为显式验证门，评审不需要猜测结果。

---

*本评审由 DS4P 独立完成，仅写入 `docs/reviews/qt-desktop-shell-ds4p-round2-review.md`。未修改任何其他文件。*
