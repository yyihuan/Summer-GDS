# 前端部署与打包

文档版本：v1.1
日期：2026-05-25
状态：操作说明

适用范围：`v2/` 的桌面 GUI 入口 `summer-gds-v2-gui`

这份文档只回答两件事：

1. 在不同平台上怎么直接启动 GUI。
2. 怎么把 GUI 打成单个可执行程序。

如果你只想先跑起来，直接看「直接启动」。

## 1. 直接启动

当前 GUI 入口是 `summer-gds-v2-gui`，对应 `summer_gds.gui.launcher:main`。

推荐启动方式：

```bash
cd v2
uv sync
uv run summer-gds-v2-gui
```

如果你已经激活了自己的虚拟环境，并且希望 `uv` 使用当前激活环境，可以改用：

```bash
cd v2
uv run --active summer-gds-v2-gui
```

如果项目依赖已经安装到当前环境，也可以直接运行已安装的命令：

```bash
summer-gds-v2-gui
```

或者：

```bash
python -m summer_gds.gui.launcher
```

如果你是第一次在某个平台上启动，建议先完成一次 `uv sync`；如果当前机器离线，前提是依赖已经在本地环境里安装好，否则任何启动方式都会因为缺包而失败。

### 1.1 macOS

- 推荐使用项目内的 `uv run summer-gds-v2-gui`。
- 如果你使用独立 Python 解释器，确保当前环境能加载 `pywebview` 的 macOS 后端。
- 如果弹出窗口启动失败，先确认 Python 是 64 位，且图形会话正常。
- 启动失败时，崩溃日志写入 `~/.summer-gds-crash.log`。

### 1.2 Windows

- 推荐使用 `uv run summer-gds-v2-gui`。
- 需要 WebView2 Runtime。Win10 21H2+ 和 Win11 已内置，无需额外操作。
- 较老版本的 Win10（21H1 及更早）需要手动安装 WebView2 Runtime：
  1. 下载 Evergreen Standalone Installer：<https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section>
  2. 选择 "x86" 或 "x64" 对应目标系统的体系结构，下载并运行 `MicrosoftEdgeWebview2Setup.exe`。
  3. 安装完成后无需重启，重新启动 Summer GDS 即可。
  4. 如果目标机器完全离线，下载 "Fixed Version" 离线包，解压后将路径设为环境变量 `WEBVIEW2_BROWSER_EXECUTABLE_FOLDER` 指向解压目录。
- 如果双击启动失败，优先从命令行运行，先看异常而不是直接打包。
- 启动失败时，崩溃日志写入 `%USERPROFILE%\.summer-gds-crash.log`。

### 1.3 Linux

- 推荐使用 `uv run summer-gds-v2-gui`。
- 如果默认后端不可用，优先安装 `pywebview[qt]`。
- 如果你想走 GTK 路线，按 pywebview 的 GTK 依赖安装系统包。
- 在 Ubuntu 上，常见依赖是 `python3-gi`、`python3-gi-cairo`、`gir1.2-gtk-3.0`、`gir1.2-webkit2-4.0`。
- 启动失败时，崩溃日志写入 `~/.summer-gds-crash.log`。

## 2. 单文件打包

当前发布目标是 PyInstaller onefile。

建议先做一次 `onedir` 验证，再切到 `onefile`。原因很简单：onefile 会把依赖解压到临时目录里再启动，排错比 onedir 更难。

### 2.1 安装打包工具

```bash
cd v2
python -m pip install pyinstaller
```

如果你已经在 `uv` 环境里，也可以在同一个环境里安装 PyInstaller。

建议在目标平台上直接构建，不要跨平台交叉打包。macOS、Windows 和 Linux 的桌面运行时依赖不同，最稳妥的方式是在各自平台上分别产出对应包。

### 2.2 先验证 onedir（推荐使用 spec 文件）

项目提供了 `v2/SummerGDS.spec`，已经配置好 klayout 动态库、matplotlib 数据文件和 GUI 静态资源的收集。推荐直接用 spec 打包：

```bash
cd v2
pyinstaller SummerGDS.spec
```

spec 文件顶部 `MODE` 变量默认为 `"onedir"`，此时产出目录在 `dist/SummerGDS/`。

这一步的目标不是发布，是确认资源文件、pywebview 后端和模板加载都正常。

如果你不想用 spec，也可以手动执行：

```bash
cd v2
pyinstaller --onedir --name SummerGDS \
  --collect-data summer_gds \
  --collect-data klayout \
  --collect-data matplotlib \
  --hidden-import klayout.db \
  --hidden-import klayout.pya \
  --hidden-import matplotlib.backends.backend_agg \
  src/summer_gds/gui/launcher.py
```

### 2.3 生成单个可执行程序

将 spec 文件中的 `MODE` 改为 `"onefile"`，然后重新执行：

```bash
cd v2
# 编辑 SummerGDS.spec: MODE = "onefile"
pyinstaller SummerGDS.spec
```

或者手动执行：

```bash
cd v2
pyinstaller --onefile --windowed --name SummerGDS \
  --collect-data summer_gds \
  --collect-data klayout \
  --collect-data matplotlib \
  --hidden-import klayout.db \
  --hidden-import klayout.pya \
  --hidden-import matplotlib.backends.backend_agg \
  src/summer_gds/gui/launcher.py
```

说明：

- `--collect-data summer_gds` 会把 `templates/`、`static/` 等包内数据一起收进去（前提是 `pyproject.toml` 的 `artifacts` 正确声明了这些非 Python 文件）。
- `--collect-data klayout` 收集 klayout 的动态库、db_plugins 等。
- `--collect-data matplotlib` 收集字体和后端配置，确保 Agg 渲染正常。
- Windows 和 macOS 上，`--windowed` 会让 GUI 不弹控制台。
- 在 Linux 上，`--windowed` 会被忽略，但命令仍然可以复用。
- macOS 最终通常会得到 `.app`，Windows 得到 `.exe`，Linux 得到单个可执行文件。
- `--onefile` 会先解压到临时目录再启动，所以首启会比 `--onedir` 稍慢，但交付更简单。
- 如果构建后启动失败，优先检查目标平台的 `pywebview` 后端和系统运行时，而不是先怀疑 YAML 或业务逻辑。
- `--windowed` 模式下启动失败不会弹控制台，崩溃日志写到 `~/.summer-gds-crash.log`，并尝试弹出 tkinter 错误对话框。

### 2.4 打包产物

发布时只保留下面这些输出之一即可：

- Windows：`dist/SummerGDS.exe`
- macOS：`dist/SummerGDS.app`
- Linux：`dist/SummerGDS`

如果后面又加了新的静态资源或模板文件，只要它们仍然放在 `summer_gds` 包里，`--collect-data summer_gds` 仍然能把它们一起打进去。同时需要在 `pyproject.toml` 的 `[tool.hatch.build.targets.wheel].artifacts` 中追加对应的 glob 模式，确保 `uv sync` 后 wheel 中包含这些文件。

## 3. 发布前检查

发布前至少确认这几项：

- 启动后能打开本地 GUI 窗口。
- 新建 `base_shape`、`via`、`rings` 都能正常打开模态框。
- `validate` 和 `preview` 没有 console error。
- `Save YAML` 和 `Export GDS` 能走完本地保存流程。
- 移动窗口尺寸不会把右侧预览挤没。
- 离线环境下双击可执行程序能正常启动（不需要网络和命令行）。

## 4. 关联文档

- 架构决策见 [前端技术架构](./frontend-architecture.md)
- 交互细节见 [前端交互与页面设计](./frontend-interaction-design.md)
- CSS tokens 和组件规范见 [前端设计系统](./frontend-design-system.md)
