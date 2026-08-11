# Qt 桌面壳第二轮评审意见处置

- 文档版本：v1.1
- 日期：2026-07-30
- 状态：已并入迁移计划 v1.3

输入：

- [DS4P 第二轮评审](./qt-desktop-shell-ds4p-round2-review.md)
- [GLM 第二轮评审](./qt-desktop-shell-glm-round2-review.md)

## 1. 结论

| Reviewer | 第二轮裁决 | 剩余 blocker | 综合判断 |
| --- | --- | --- | --- |
| DS4P | `APPROVE` | 无 | 架构、并发、生命周期、打包和平台证据边界均已闭合 |
| GLM | `READY_WITH_CHANGES` | R1：pywebview launcher 测试在 Phase 2/5 间的保留与替换阶段未写死 | 意见成立；属于测试迁移顺序缺口，不改变目标架构 |

两份评审对核心方案没有分歧。唯一实质差异是：

- DS4P 将 `tests/gui/test_launcher.py` 的迁移视为已计划的实施细节。
- GLM 进一步核对当前测试代码后，指出原计划中的“更新 import 和 fakes”
  仍允许三种互不兼容的实施路径。

GLM 的证据具体且可复现：当前 `test_launcher.py` 在 import、fake 和断言层面
都绑定 pywebview；如果 Phase 5 删除 `desktop.py`/依赖而不同时替换测试，pytest
会在收集或运行时失败。因此 R1 接受，并在 v1.3 中写成唯一迁移顺序。

综合两份评审并重新逐段核对计划时，还发现三处 reviewer 没有作为 blocker
单列、但如果继续留白会让实施者产生分叉的缺口：PySide6 的依赖引入阶段、
自动 bundle probe 的每次运行控制协议，以及 shutdown 中
`RequestGate.wait_drained()` 的实际调用位置。它们不改变目标技术路线，但都
必须在实施前写死，因此一并纳入本次处置。

## 2. 处置矩阵

| 编号 | 来源 | 级别 | 处置 | v1.3 定案 |
| --- | --- | --- | --- | --- |
| R2-01 | GLM R1/T-R1 | Blocker | 接受并细化 | Phase 2 只迁移 runtime 测试，保留全部 pywebview 专属 launcher/dialog 测试；Phase 5 在 Qt 入口切换的同一阶段删除这些测试并以 Qt 等价测试替换 |
| R2-02 | GLM T-R2 | 非阻塞 | 接受 | Phase 3 命名加入不同 request ID 的并发 preview 测试 |
| R2-03 | GLM T-R3 | 非阻塞 | 接受并分阶段 | Phase 2 实现并单测 framework-neutral `RequestGate`；Phase 4 接入 Flask 并测试 HTTP 503 `app_closing` 与 in-flight drain |
| R2-04 | GLM T-R4 | 可选强化 | 接受 | bundle verifier 自动检查关键 Qt 库只有一个独立来源，KLayout 依赖不得解析到第二套 Qt |
| R2-05 | GLM T-R5 | 可选强化 | 接受并限域 | 仅创建 `QApplication` 的单元测试在首次 import PySide6 前设置 `QT_QPA_PLATFORM=offscreen`；不写入产品环境，不用于真实 WebEngine/bundle smoke |
| R2-06 | DS4P 实施顺序建议 1 | 非阻塞 | 被 R2-01 取代 | 不专门把旧 adapter 改成延迟 import；Phase 2 保持旧壳可测，Phase 5 原子切换并删除旧 import |
| R2-07 | DS4P 实施顺序建议 2 | 非阻塞 | 已覆盖 | token purge 已在 v1.1 规定于 dialog 前和成功插入前执行，无需新增语义 |
| R2-08 | DS4P 实施顺序建议 3 | 非阻塞 | 接受并前移 | Phase 1 probe 通过后即加入并锁定 PySide6/PyInstaller，同时保留 pywebview；Phase 5 只负责入口/测试切换和移除 pywebview |
| R2-09 | 综合核对 | 实施阻塞歧义 | 接受并定义协议 | 增加 frozen-only、256-bit run ID、私有 temp root、ready/command/complete marker 和 deterministic path adapter；自动退出只调用同一 Qt coordinator |
| R2-10 | 综合核对 | 生命周期高风险 | 接受并写死 | server shutdown/join 与 `RequestGate.wait_drained()` 共用一个 10 秒 deadline；serve 和 gate 均收敛后才 `session.close()`；GUI watchdog 胜出时保留 session 并拒绝晚到清理 |
| R2-11 | DS4P 图谱结论措辞 | 表述校正 | 限定适用范围 | 保持稳定的是 `SaveFileDialog`/GUI API 与业务语义；`GuiSession` 实现仍会加入 `DialogFailure` 映射、token lock/purge 和显式 close，不能称代码不变 |
| R2-12 | 最终一致性核对 | 图文顺序 | 接受并修图 | 门槛图明确 Phase 4 为 pre-cutover direct Qt-shell smoke，Phase 5 cutover 后才是 Phase 6 完整 source workflow，随后进入 bundle |

综合时另发现一个两份评审都未单独列出的阶段依赖：Phase 3 的 Qt dialog
测试和 Phase 4 的 Qt shell 实现都需要 PySide6，因此不能等到 Phase 5 才把
PySide6 加入项目环境。v1.3 将依赖引入前移到 Phase 1：

- 先在隔离环境完成精确版本 probe。
- probe 通过后，把 `PySide6==6.11.1` 加入 runtime dependencies，
  `pyinstaller==6.21.0` 加入 packaging group，并更新 `uv.lock`。
- pywebview 保留到 Phase 5，确保 Phase 1-4 的旧壳基线仍可运行；不增加双壳
  用户入口。

最终一致性核对又把既有处置写得更窄：R2-03 增加 Flask request-local
enter/leave 配对，R2-05 排除执行过晚的普通 fixture，R2-09 增加
try/finally、app watchdog、hard-kill failure 和 complete marker 成功条件，
R2-12 同步门槛图与 Phase 顺序。这些是既有决定的可执行化，不改变方案选择。

## 3. 唯一的测试迁移顺序

### Phase 2：只拆 runtime 测试

新增 `tests/gui/test_runtime.py`，从当前
`tests/gui/test_launcher.py` 移入：

- `test_loopback_server_serves_gui_and_stops`
- runtime 所需的 `urlopen` import
- 新的 ready/timeout/idempotent stop 和 `RequestGate` 单元测试

本阶段：

- `test_launcher.py` 改为从 `runtime.py` 取得 runtime 边界时所需的最小 import；
  如果 loopback 测试已完全移出，则删除该文件中不再使用的
  `start_loopback_server`/`urlopen` import。
- `FakeWebviewModule`、`FakeWindow`、
  `test_launch_desktop_forces_edgechromium_on_windows` 和全部
  `test_pywebview_*` 保留。
- 只在 runtime `stop()` 签名变化时同步调整 `FakeServerHandle`。
- pywebview 仍是当前生产壳，因此这一阶段不能把 fakes 提前改造成 Qt fakes。

Phase 2 完成时，旧壳测试和新 runtime 测试必须同时收集并通过。

### Phase 5：原子替换 launcher 测试

按顺序执行：

1. 确认 Phase 1 已锁定的 PySide6/PyInstaller 和 import probe 仍通过；此时
   pywebview 尚未移除。
2. 把 `launcher.py` 切换到 Qt shell。
3. 从 `test_launcher.py` 删除
   `PyWebviewSaveFileDialog` import、`FakeWebviewModule`、`FakeWindow`、
   edgechromium 测试和全部 `test_pywebview_*`。
4. 增加不创建真实 WebEngine 的 Qt 等价测试：
   - `test_launcher_delegates_to_qt_shell`
   - `test_launcher_propagates_qt_exit_code`
   - `test_launcher_reports_qt_shell_failure`
   - 干净子进程中的 `test_gui_launch_path_does_not_import_pywebview_stack`
5. Qt dialog 的选择、取消、异常、超时和 shutdown 行为由
   `tests/gui/qt_unit/test_qt_dialog.py` 负责，不在 launcher 测试中重复。
6. 删除 `desktop.py`、pywebview dependency 和生产 import。
7. 重新执行 pytest collect/full suite 和 import-boundary tests。

该顺序避免：

- Phase 2 过早制造不存在的 Qt shell fake。
- Phase 5 删除 `desktop.py` 后测试收集失败。
- 为了保留旧测试而让 pywebview 悄然留在生产依赖。

## 4. 新增的可执行门槛

### 4.1 RequestGate

Phase 2 单元测试：

- `test_request_gate_rejects_new_entries_after_begin_shutdown`
- `test_request_gate_waits_for_inflight_requests`
- `test_request_gate_leave_wakes_waiter`

Phase 4 Flask 集成测试：

- `test_api_returns_503_app_closing_after_gate_shutdown`
- `test_shutdown_waits_only_for_already_inflight_requests`
- `test_rejected_request_does_not_decrement_inflight`
- `test_request_leaves_gate_exactly_once`
- `test_shutdown_does_not_close_session_before_gate_drains`
- `test_gate_timeout_preserves_session_directory`
- `test_server_close_runs_once_on_timeout`
- `test_shutdown_watchdog_rejects_late_worker_cleanup`

shutdown thread 必须实际调用
`RequestGate.wait_drained(max(0, deadline - time.monotonic()))`。server join 和
gate drain 共享一个 10 秒 deadline；只有两者都成功，才允许
`session.close()`。GUI hard-deadline watchdog 若先取得 terminal state，晚到
worker 只能结束自身，不能再清理 session。

Flask 必须只在 session-token 鉴权成功后调用原子 `try_enter()`，并把成功结果
保存为 request-local flag；`teardown_request` 清除 flag 后仅对成功 enter 的
请求调用一次 `leave()`。403、closing 503 和页面请求都不得 decrement。

### 4.2 preview 并发

Phase 3 增加：

- `test_concurrent_preview_with_distinct_request_ids_does_not_clobber`

它必须用 barrier/fake renderer 强制两个不同 `request_id` 重叠执行，证明临时
文件互不覆盖、互不删除，两个请求都得到各自的合法响应；不能依赖真实渲染
速度形成偶然通过。

### 4.3 offscreen 边界

- 只有创建 `QApplication`、但不创建 `QWebEngineView` 的单元测试使用
  `QT_QPA_PLATFORM=offscreen`。
- 这些测试固定在 `tests/gui/qt_unit/`；其 `conftest.py` 在 test module
  collection 前断言 PySide6 尚未导入，再设置环境变量。普通 pytest fixture
  执行太晚，不得承担初始化。
- 不在应用启动器、用户环境、spec 或 bundle verifier 中设置它。
- macOS source real-window 和 bundle smoke 必须使用真实 platform plugin。

### 4.4 单一 Qt 来源

`verify_desktop_bundle.py` 除动态库绝对路径检查外，还必须：

- 生成关键 Qt 库的 normalized dependency inventory，至少覆盖
  Qt6Core、Qt6Gui、Qt6Widgets、Qt6Network、Qt6WebEngineCore 和
  Qt6WebEngineWidgets。
- 每条依赖记录 loader 声明、解析后的 bundle-relative path、canonical
  realpath、SHA-256，以及 Mach-O install name/framework root 或 PE 实际
  DLL 来源。
- symlink/helper 对同一 canonical entity 的引用允许；同一逻辑库存在两个
  独立 canonical 文件或 bundle root 时失败，即使 hash 相同。
- 若 KLayout extension 存在 Qt 依赖，解析结果必须与 PySide6 使用同一
  canonical 来源；完全不依赖 Qt 也是合法结果。
- 把 inventory 保存为构建证据，供 macOS `otool -L` 和 Windows
  `dumpbin /dependents` 结果交叉核对。

### 4.5 私有 bundle probe

原计划要求自动等待 app-ready、执行 YAML/SVG/GDS 并优雅退出，但没有定义
如何发现随机端口、隔离旧日志、取得真实 session/path token，或触发 Qt
coordinator。v1.3 固定为：

- frozen-only 双环境变量激活，256-bit `run_id` 和当前用户私有 temp root。
- ready/command/complete 三个原子 JSON 文件；marker 不包含 token。
- verifier 从 ready marker 的 origin GET 页面，提取现有 session token，
  再用禁用 proxy/redirect 的 client 调用现有鉴权 API；origin 只接受精确的
  `http://127.0.0.1:<port>`。
- deterministic dialog 只能映射到本次 root 的固定 input/output 文件；
  真实 `QFileDialog` 仍由独立目视 smoke 验收。
- verifier 不论业务 probe 成败都在 `finally` 发布合法 shutdown command；
  shell 另有 180 秒总 watchdog，195 秒后仍失控才允许 verifier 强制终止并
  判失败。
- GUI-thread `QTimer` 只接受 matching `shutdown` command，并委托 §6.5
  的同一 coordinator；不新增 HTTP quit route，不使用 SIGTERM 假装优雅退出。
- verifier 同时核对 run ID/PID、输出、KLayout read-back、complete cleanup、
  退出码、端口和 session 残留。
- complete marker 只证明 app cleanup；业务 probe 失败不能被 cleanup 成功
  覆盖。只有合法 command、正常 coordinator 和全部 cleanup 条件成立时
  `result` 才能为 `ok`。

完整 schema、权限、路径和失败语义只在
[迁移计划 §7.4.1](../planning/qt-desktop-shell-migration-plan.md)
维护，本处不复制第二份规范。

## 5. 实施就绪判断

v1.3 接受了 GLM 明示的唯一 blocker R1，并把所有第二轮强化和综合核对缺口
变成命名测试、协议或阶段 gate。因此主任务的处置结论是：

- 第一轮所有 blocker 已关闭。
- 第二轮没有未处置 blocker。
- 目标架构、测试迁移顺序、bundle 验收控制面和 shutdown drain 已形成单一
  可实施契约。
- 可以进入 Phase 1，但这不表示代码、macOS bundle 或 Windows 兼容性已经完成。

这是对两份评审条件的综合处置，不伪称 reviewer 已对 v1.3 重新给出第三轮裁决。
