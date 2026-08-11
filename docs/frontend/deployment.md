# 前端部署与打包

文档版本：v1.3
日期：2026-08-06
状态：Qt 桌面壳 macOS 实施记录；Windows 原生 AMD64 自动 bundle gate 已通过，真实用户会话目视验收待完成

适用范围：项目根目录的桌面 GUI 入口 `summer-gds-gui`。

## 1. 运行架构

桌面入口固定为：

```text
summer-gds-gui
  -> PySide6 QMainWindow / QtWebEngine
  -> Flask 127.0.0.1 随机端口
  -> 现有 Web UI、YAML v2、geometry 和 writer
```

![Qt 桌面壳目标架构](../diagrams/qt-desktop-shell-target-architecture.svg)

可编辑图源：
[`qt-desktop-shell-target-architecture.mmd`](../diagrams/qt-desktop-shell-target-architecture.mmd)。

不提供双壳参数、HTTP quit route、renderer 环境变量配置或系统浏览器生产入口。

## 2. Source run

```bash
uv sync --frozen --group packaging
uv run summer-gds-gui
```

运行时只监听 `127.0.0.1` 随机端口。QtWebEngine profile 为
off-the-record；窗口关闭由唯一 shutdown coordinator 停止 server、排空已进入
的 API request、清理 session，再退出 Qt event loop。

macOS 真实窗口测试不得设置 `QT_QPA_PLATFORM=offscreen`。`offscreen` 只用于
`tests/gui/qt_unit/` 的 Qt dialog 单元测试。

## 3. macOS onedir

根目录 [SummerGDS.spec](../../SummerGDS.spec) 是唯一权威打包配置：

```bash
uv run pyinstaller --noconfirm SummerGDS.spec
uv run python scripts/verify_desktop_bundle.py dist/SummerGDS.app
```

当前交付目标是 windowed onedir `.app`，不是 onefile。spec 使用 PyInstaller
内置 PySide6 hooks，显式收集 WebEngine 实际 import；KLayout 只声明生产
import 和动态加载的 GDS plugin，不使用 `collect_all("PySide6")`、
`collect_submodules("klayout")` 或全量 KLayout dynamic libraries。

verifier 必须验证：

- cocoa platform plugin、QtWebEngine helper/resources/locales；
- 生产 TOC 不含 pywebview/pythonnet/clr；
- Web UI 静态资源 hash 与源码一致；
- Mach-O 不引用项目、`.venv` 或构建机非系统绝对库；
- Qt/KLayout 没有第二套独立 Qt 来源；
- 从仓库外 Unicode/空格目录启动；
- frozen-only ready/command/complete marker；
- 真实鉴权 API 的 YAML、SVG、GDS 与 KLayout read-back；
- coordinator 正常 shutdown、端口/session cleanup 和退出码。

PyInstaller 的 Matplotlib runtime hook 会为每次进程创建私有 config 目录。
spec 因此随包携带构建时字体缓存，launcher 在导入 `font_manager` 前把缓存复制
到本次私有目录，避免每次 frozen 启动重建字体索引。该行为是应用内部部署细节，
不要求用户设置环境变量。

## 4. Windows 原生 AMD64 onedir

在原生 AMD64 Windows 主机上执行以下自动验证；命令不增加第二个桌面壳、用户环境变量或开发框架安装要求：

```powershell
uv sync --frozen --group dev --group packaging
uv run pyinstaller --noconfirm SummerGDS.spec
uv run python scripts/verify_desktop_bundle.py dist\SummerGDS --dependency-inventory build\windows-qt-dependency-inventory.json
```

![Windows AMD64 bundle 验证流程](../diagrams/windows-amd64-bundle-verification.svg)

可编辑图源：
[`windows-amd64-bundle-verification.mmd`](../diagrams/windows-amd64-bundle-verification.mmd)。

`verify_desktop_bundle.py` 按实际 PyInstaller onedir runtime payload 布局检查：

- qwindows platform plugin、WebEngine helper/resources/locales 与静态 Web UI；
- Windows PE import 的 Qt6Core、Qt6Gui、Qt6Widgets、Qt6Network、Qt6WebEngineCore、Qt6WebEngineWidgets 各只有一个 bundle 内 canonical DLL 来源；
- KLayout GDS plugin 同时位于 runtime payload 的 `db_plugins` 与 `klayout/db_plugins`，两份内容 hash 相同；
- 复制后的 frozen-only probe 通过鉴权 API 执行 YAML、SVG、GDS 与 KLayout read-back，并以唯一 shutdown coordinator 得到完整 cleanup marker 和零退出码。

当前自动证据来自 Windows 11 Pro 10.0.26120、原生 AMD64 进程、Python 3.13.14 x64。该主机的 SSH 命令运行在非交互 session，不能替代已登录用户会话中的普通窗口目视流程；后者仍须验证真实 `QFileDialog`、cancel、Unicode 路径和关闭后的窗口体验。

## 5. 平台状态

- macOS source-run：Python 3.13.3、PySide6 6.11.1、KLayout 0.30.8 的真实
  cocoa 窗口已验证。
- 当前 macOS 宿主为 Apple Silicon，但构建进程和产物为 x86_64 translated。
  新复制路径会触发 QtWebEngineProcess 的 Rosetta AOT，严格 60 秒 cold-ready
  gate 当前仍可能超时；这不是原生 ARM 证据。
- Windows 原生 AMD64：自动 source/bundle 测试与 moved-bundle verifier 已通过；真实用户会话目视验收仍待完成。
- Windows ARM 只可作为 AMD64/x64 emulation 证据，不声明 native ARM 或正式 Windows x64 支持。
- 正式 Windows x64 支持仍要求干净原生 Windows 11 x64 环境、真实用户会话目视验收及发布流程。

禁止把 source run、已热身的同一路径启动、Rosetta/emulation 或进程存活替代
全新的 moved-bundle gate。

## 6. 日志

- debug：`~/.summer-gds-debug.log`
- 最近一次启动失败：`~/.summer-gds-crash.log`

日志不得记录 session token、path token、YAML 全文或未脱敏请求体。
