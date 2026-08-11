# Summer GDS

送给我最爱的夏夏~ 希望可以帮助她更加轻松地工作 ❤️

Summer GDS 是一个基于 KLayout 的 GDS 版图生成工具，通过 YAML 配置描述几何对象，自动完成几何计算并输出 GDS 文件和预览图像。

**当前版本支持：**

- 三类几何对象：`base_shape`（基础多边形）、`via`（通孔，基于已有图形扩展出环,达成溅铝和刻孔的效果）、`rings`（环阵列）
- 每个对象支持独立的 layer 配置和逐角配置倒角（fillet）或同心倒角
- 对象之间通过 `sid` 引用：可以基于已有图形做 offset 生成新图形，无需手工重复计算坐标
- 输出格式：GDS 文件、PNG 图像、SVG 图像
- 两种使用方式：CLI（命令行）和 GUI（桌面窗口）

## 目录结构

```
Summer-GDS/
├── src/summer_gds/          # 源码（Python src-layout）
│   ├── cli.py               # CLI 入口
│   ├── app/                 # 编排层（pipeline、export service）
│   ├── schema/              # YAML v2 解析与协议错误
│   ├── model/               # 内部数据模型
│   ├── geometry/            # 几何计算（fillet、Region 转换、offset）
│   ├── writer/              # 输出 backend（GDS writer、image renderer）
│   └── gui/                 # 桌面 GUI（PySide6 + QtWebEngine + Flask loopback）
│       ├── templates/
│       └── static/
├── tests/                   # 测试
├── docs/                    # 设计文档
├── summer_gds_v1/           # v1 代码存档（仅开发仓库保留）
├── pyproject.toml
├── SummerGDS.spec           # PyInstaller 打包配置
└── uv.lock
```

## 安装与运行

要求 Python >= 3.13，使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

```bash
uv sync
```

### CLI

```bash
# 校验 YAML 配置
uv run summer-gds validate config.yaml

# 导出 GDS
uv run summer-gds export config.yaml --format gds --out layout.gds

# 导出预览图
uv run summer-gds export config.yaml --format png --out preview.png
uv run summer-gds export config.yaml --format svg --out preview.svg

# 快捷命令
uv run summer-gds generate config.yaml --out layout.gds
uv run summer-gds preview config.yaml --format png --out preview.png
```

### GUI

```bash
uv run summer-gds-gui
```

### 打包为可执行文件

```bash
uv sync --frozen --group packaging
uv run pyinstaller --noconfirm SummerGDS.spec
```

根目录 `SummerGDS.spec` 是唯一权威配置，产物为 QtWebEngine 所需资源齐全的
onedir 包，位于 `dist/`。建议在目标平台上直接构建；详细验证流程见
[前端部署与打包文档](./docs/frontend/deployment.md)。

## YAML 配置示例

```yaml
schema_version: 2

global:
  unit: um
  dbu: 0.001

gds:
  top_cell: TOP
  output: build/layout.gds

shapes:
  - type: base_shape
    sid: 0
    name: source_pad
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
    fillet:
      radius: 2

  - type: base_shape
    sid: 1
    name: source_pad_margin
    layer: [2, 0]
    source:
      ref: 0
      offset: 10
    fillet:
      radius: 2

  - type: via
    sid: 2
    name: contact_window
    layer: [10, 0]
    source:
      ref: 0
    offsets:
      inner: -5
      outer: 8
    fillet:
      inner: { radius: 1 }
      outer: { radius: 2 }

  - type: rings
    sid: 3
    name: guard_rings
    layer: [20, 0]
    source:
      ref: 0
    count: 3
    pitch: 12
    width: 4
    fillet:
      rings:
        - inner: { radius: 1 }
          outer: { radius: 2 }
        - inner: { radius: 1 }
          outer: { radius: 2 }
        - inner: { radius: 1 }
          outer: { radius: 2 }
```

## v1 到 v2 的变化

v1 基于 PySide6 GUI + Flask 后端。v2 重构为 CLI-first 设计（CLI 是稳定执行
入口，GUI 和脚本都通过 YAML 交互）和统一几何流水线（`YAML 业务对象 → 编译 →
KLayout Region → output backend`）；当前桌面壳使用 `PySide6 + QtWebEngine +
Flask loopback`，保留既有 Web UI、YAML v2 和几何/GDS 语义。v1 代码仅作为
开发仓库中的历史存档，客户源代码包不包含它。
