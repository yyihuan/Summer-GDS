# 前端部署与打包

文档版本：v1.0
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

### 1.2 Windows

- 推荐使用 `uv run summer-gds-v2-gui`。
- 需要可用的 WebView2 Runtime。
- 如果双击启动失败，优先从命令行运行，先看异常而不是直接打包。

### 1.3 Linux

- 推荐使用 `uv run summer-gds-v2-gui`。
- 如果默认后端不可用，优先安装 `pywebview[qt]`。
- 如果你想走 GTK 路线，按 pywebview 的 GTK 依赖安装系统包。
- 在 Ubuntu 上，常见依赖是 `python3-gi`、`python3-gi-cairo`、`gir1.2-gtk-3.0`、`gir1.2-webkit2-4.0`。

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

### 2.2 先验证 onedir

```bash
cd v2
pyinstaller --onedir --name SummerGDS \
  --collect-data summer_gds \
  src/summer_gds/gui/launcher.py
```

这一步的目标不是发布，是确认资源文件、pywebview 后端和模板加载都正常。

### 2.3 生成单个可执行程序

```bash
cd v2
pyinstaller --onefile --windowed --name SummerGDS \
  --collect-data summer_gds \
  src/summer_gds/gui/launcher.py
```

说明：

- `--collect-data summer_gds` 会把 `templates/`、`static/` 等包内数据一起收进去。
- Windows 和 macOS 上，`--windowed` 会让 GUI 不弹控制台。
- 在 Linux 上，`--windowed` 会被忽略，但命令仍然可以复用。
- macOS 最终通常会得到 `.app`，Windows 得到 `.exe`，Linux 得到单个可执行文件。
- `--onefile` 会先解压到临时目录再启动，所以首启会比 `--onedir` 稍慢，但交付更简单。
- 如果构建后启动失败，优先检查目标平台的 `pywebview` 后端和系统运行时，而不是先怀疑 YAML 或业务逻辑。

### 2.4 打包产物

发布时只保留下面这些输出之一即可：

- Windows：`dist/SummerGDS.exe`
- macOS：`dist/SummerGDS.app`
- Linux：`dist/SummerGDS`

如果后面又加了新的静态资源或模板文件，只要它们仍然放在 `summer_gds` 包里，`--collect-data summer_gds` 仍然能把它们一起打进去。

## 3. 发布前检查

发布前至少确认这几项：

- 启动后能打开本地 GUI 窗口。
- 新建 `base_shape`、`via`、`rings` 都能正常打开模态框。
- `validate` 和 `preview` 没有 console error。
- `Save YAML` 和 `Export GDS` 能走完本地保存流程。
- 移动窗口尺寸不会把右侧预览挤没。

## 4. 关联文档

- 架构决策见 [前端技术架构](./frontend-architecture.md)
- 交互细节见 [前端交互与页面设计](./frontend-interaction-design.md)
- CSS tokens 和组件规范见 [前端设计系统](./frontend-design-system.md)
