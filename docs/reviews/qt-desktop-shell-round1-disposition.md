# Qt 桌面壳第一轮评审意见处置

- 文档版本：v1.0
- 日期：2026-07-29
- 状态：已并入迁移计划 v1.1

输入：

- [DS4P 第一轮评审](./qt-desktop-shell-ds4p-review.md)
- [GLM 第一轮评审](./qt-desktop-shell-glm-review.md)

## 1. 处置原则

两份评审都认可继续使用 Web UI，并认为
`PySide6 + QtWebEngine + Flask` 可以进入实施，但都要求先消除打包和生命周期
歧义。本文件不是把全部建议机械合并，而是记录每项关键意见的采用方式。

处置规则：

- 与实际代码和可重复证据一致的意见直接接受。
- 两份评审给出不同参数时，以现有前端契约、失败边界和可测试性定案。
- 依赖未提供可靠平台能力时，不把“可能可用”写成支持承诺。
- 不为测试便利增加用户可见功能，也不采用会扩大冻结包和原生库冲突面的
  无边界收集策略。
- 第一轮 reviewer 的建议不是新的权威来源；最终实现契约以
  [迁移计划 v1.1](../planning/qt-desktop-shell-migration-plan.md) 为准。

## 2. 重新核实的基线事实

| 事实 | 当前证据 | 对计划的影响 |
| --- | --- | --- |
| Graphify 图谱基线 | `.graphify/GRAPH_REPORT.md` 记录 commit `dc4d0dd`，与当前 `HEAD` 一致 | 图谱可用于理解迁移前代码；实施改动后必须重建 |
| pytest 基线 | `84 tests collected`，`84 passed` | 后续只使用“collected items”口径，不称“84 个测试函数” |
| 前端对话框超时 | `app.js` 的 `FILE_DIALOG_TIMEOUT_MS = 120000` | worker 超时固定为 100 秒，给 HTTP/前端留 20 秒余量 |
| `GuiSession` 共享状态 | `path_tokens` 是 Flask worker 共享的可变字典，当前无锁；过期清理函数未被调用 | 增加普通 `threading.Lock`，不使用 `RLock` |
| KLayout 实际 import | 生产源码只 `import pya`；本机 import trace 触发 `klayout.db`、`klayout.pya`、`klayout.tl`，未触发 `lay`、`rdb`、`lib`、`pex` | 删除 `collect_submodules("klayout")` 和未使用 GUI/扩展 hiddenimports，以冻结产物 smoke 证明最小集合足够 |
| 当前 spec 权威性 | 仓库根 `SummerGDS.spec` 是 tracked 文件；`tests/SummerGDS.spec` 是用户已有的 untracked 副本 | 只修改根 spec；不删除、不提交、不覆盖用户副本 |
| 当前可复现版本候选 | PyPI 当前提供 `PySide6 6.11.1` 和 `PyInstaller 6.21.0`；项目 lock 当前为 KLayout `0.30.8` | 迁移分支先锁定这一组合，升级必须重新通过 source/bundle gate |
| Windows ARM wheel 交集 | PySide6/PyInstaller 有 Windows ARM64 wheel，但 KLayout `0.30.8` 没有；三者共同提供 Windows AMD64 wheel | Parallels Windows ARM 阶段只验证 AMD64 构建在 x64 emulation 下运行，不做 native ARM 声明 |
| Flask teardown | `SUMMER_GDS_CLOSE_ON_TEARDOWN` 未设置，因此 teardown 不负责关闭 `GuiSession` | Qt 生命周期必须显式、且仅一次调用 `session.close()` |
| v1 正向证据边界 | v1 使用 QtWebEngine，但保存路径走 `downloadRequested`，不是 v2 的 worker-to-GUI bridge | v1 只证明桌面承载路径，不证明新桥或冻结包完整性 |

## 3. 综合处置矩阵

| 决策 | 来源 | 处置 | 定案 |
| --- | --- | --- | --- |
| D01 冻结打包策略 | DS4P B1/H5，GLM M5/M6/T5 | 调整后接受 | 直接 import 所需 Qt 模块，优先使用锁定版 PyInstaller 内置 PySide6 hooks；禁止默认 `collect_all("PySide6")`。构建后按资源清单和真实启动验证 |
| D02 path token 线程安全 | DS4P B2/H8 | 接受 | `path_tokens` 全部读写、清理和 `close()` 清空由一个普通 `Lock` 保护；dialog 打开期间不持锁；选择入口和 token resolve 均清理过期项 |
| D03 KLayout/Qt 冲突面 | DS4P B3 | 接受并收窄 | 先移除未实际 import 的 KLayout GUI/扩展模块和 `collect_submodules`；再用 macOS/Windows 产物依赖清单确认没有第二套 Qt |
| D04 dialog 等待超时 | DS4P B4 建议 30 秒，GLM B2 建议 100 秒 | 采用 100 秒 | 30 秒会把正常人工选路误判为失败；100 秒小于既有 120 秒前端超时。超时状态不可被晚到结果覆盖 |
| D05 并发 dialog | GLM B1/B5 | 接受并修正响应 | single-flight；第二个请求立即返回 `dialog_busy`，不排队、不打开第二个 modal。`canceled=false`，因为 busy 不是用户取消 |
| D06 HTTP 客户端断连 | GLM B2 | 不作为正确性依赖 | 同步 Flask/Werkzeug 没有可靠、跨平台的请求断连取消信号。实现依靠 100 秒硬超时；未来若能观测断连，只作为提前取消优化 |
| D07 late result 与 token | GLM B2 | 接受目标、调整机制 | bridge 超时后将 request 标记终态并要求 GUI 关闭 dialog；晚到路径被丢弃。只有 bridge 成功返回路径后 `GuiSession` 才创建 token，因此不需要“回滚未发送 token” |
| D08 跨线程异常 | GLM B3 | 接受 | framework-neutral `DialogFailure` 映射为 HTTP 200 的应用错误；`dialog_error`/`dialog_timeout`/`dialog_busy` 均 `canceled=false`；用户取消才是 `canceled=true` |
| D09 WebEngine profile | DS4P L1，GLM B4 | 接受 | 使用无 storage name 的独立 off-the-record profile；不写 cookie/cache/profile 目录 |
| D10 renderer crash | DS4P H2/M6/O7 | 调整后接受 | 监听并记录 `renderProcessTerminated`；异常终止时取消 pending dialog、显示原生致命错误并退出。首版不自动 reload，避免悄然丢失未保存 UI 状态或形成 crash loop |
| D11 JavaScript 可见性 | DS4P H4 | 接受核心项 | 自定义 `QWebEnginePage` 转发 console warning/error；`loadFinished` 后检查 `#app`、`#workspace` 和显式 app-ready marker。首版不引入 QWebChannel heartbeat |
| D12 Flask production/ready | DS4P H6/M4/O4 | 接受 | `DEBUG`、`TESTING` 和 debugger 保持关闭；不用 `app.run`/reloader。server thread 启动后做有界 loopback GET，再向 WebEngine 交付 URL |
| D13 依赖锁定 | DS4P M3/O2，GLM M2 | 调整后接受 | 初始实施候选精确锁定 `PySide6==6.11.1`、`PyInstaller==6.21.0`；由 `uv.lock` 固化传递依赖。不是宽泛的 `>=6.8,<7` |
| D14 Windows ARM 定位 | DS4P H3，GLM Phase 8 | 收窄 | 由于 KLayout 缺 Windows ARM64 wheel，现阶段唯一完整 wheel 交集是 AMD64。ARM VM 只跑 AMD64/x64 emulation |
| D15 测试拆分 | GLM M3/M4/T1-T6 | 接受 | bridge 状态机、runtime 和 import boundary 用无 WebEngine 单测；真实 WebEngine 与冻结包另设 source/bundle smoke；Phase 2 同步迁移 launcher tests |
| D16 `collect_all("PySide6")` | GLM M6 | 不采用 | 它会带入未使用 Qt 模块、插件和原生库，增加体积与冲突面；只有内置 hooks 被证实漏收且无法做最小补充时，才作为诊断实验 |
| D17 bundle 绝对路径检查 | GLM M5/T5 | 调整后接受 | 不对所有二进制做脆弱的全局 `/Users/` 字符串断言；检查 PyInstaller warning/TOC、目标动态库解析，并把 bundle 移到含空格/Unicode 的新目录、用净化环境真实启动 |
| D18 许可证门槛 | DS4P H1 | 接受并前移 | Phase 1 产出依赖许可证清单和分发检查表；可分发 bundle 前必须完成 notices 和替换/重链接说明的合规确认。该步骤不是法律意见 |
| D19 headless product flag | DS4P O1 | 不采用 | headless 不验证 QWebEngine 桌面壳，且会扩大对外 CLI 契约。使用内部 bundle probe、offscreen 单测和真实窗口 smoke，不新增用户参数 |
| D20 日志/Unicode/内存 | DS4P M5/M7/O3/O5/O6 | 接受 | debug log 采用 1 MiB、3 备份轮转；自动覆盖中文、emoji、空格路径；记录 source/bundle 冷启动时间、稳定内存和产物大小，作为趋势基线而非发布阈值 |

## 4. 明确的响应语义

文件对话框 API 继续使用 HTTP 200 承载应用层结果：

| 场景 | `ok` | `canceled` | error code | 是否创建 path token |
| --- | --- | --- | --- | --- |
| 用户选择路径 | `true` | 不返回 | 无 | save dialog 创建 |
| 用户点击取消 | `false` | `true` | 无 | 否 |
| 已有 dialog | `false` | `false` | `dialog_busy` | 否 |
| worker 100 秒超时 | `false` | `false` | `dialog_timeout` | 否 |
| Qt 执行异常 | `false` | `false` | `dialog_error` | 否 |
| 应用正在关闭 | `false` | `true` | 无 | 否 |

前端 120 秒 fetch 超时保持不变。后端应先在 100 秒结束，使前端通常能收到
结构化错误；网络层异常仍走现有 `handleRequestError`。

## 5. 第二轮评审门槛

第二轮 reviewer 应只判断以下问题：

1. v1.1 是否逐项关闭第一轮 blocker 和 blocking ambiguity。
2. 被调整或不采用的建议是否有可靠理由，是否留下新的 correctness gap。
3. dialog 状态机和 shutdown 是否存在死锁、双完成、晚结果回写或资源清理竞态。
4. PyInstaller 策略是否足够具体，同时避免无边界收集。
5. macOS 本地、Windows ARM x64 emulation 和原生 Windows x64 三类证据是否仍被严格区分。
