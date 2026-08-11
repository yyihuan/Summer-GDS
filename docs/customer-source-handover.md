# 客户源代码包说明

客户源代码包从已提交的 Git revision 生成，保证其内容可追溯、可重建，且不携带
本机缓存或开发过程材料。

## 包含内容

- `src/summer_gds/`：当前 v2 应用源码与本地 Web UI；
- `tests/`：v2 自动测试（不含任何用户本机未跟踪文件）；
- `SummerGDS.spec`、`pyproject.toml`、`uv.lock`：可复现依赖与 onedir 打包配置；
- `packaging/`：打包图标等必要资源；
- `docs/`：架构、协议、质量、前端与部署文档；
- 根目录 `README.md` 和生成脚本。

## 刻意排除

- `.graphify/`：内部代码图谱、缓存和工作台输出；
- `docs/reviews/`、`docs/tmp/`：评审请求、处置过程和临时工作材料；
- `summer_gds_v1/`：已归档的旧版本；
- `.venv/`、`build/`、`dist/`、`.pytest_cache/`、`.gstack/`、`.DS_Store`：本机
  环境、构建产物、测试缓存与工具日志；
- `tests/SummerGDS.spec`：用户本机未跟踪文件，不属于项目交付内容。

## 重建

在目标平台安装 Python 3.13 和 `uv` 后：

```bash
uv sync --frozen --group dev --group packaging
uv run pytest -q
uv run pyinstaller --noconfirm SummerGDS.spec
```

Windows AMD64 onedir 的冻结包验证：

```powershell
uv run python scripts/verify_desktop_bundle.py dist\SummerGDS --dependency-inventory build\windows-qt-dependency-inventory.json
```

Windows ARM 主机上的 AMD64/x64 仿真仅是兼容性证据，不声明原生 ARM 或正式
Windows x64 发布支持。

## 生成归档

从已提交 revision 生成客户包：

```bash
python scripts/create_customer_source_archive.py --revision HEAD --output artifacts/Summer-GDS-source.tar.gz
```

归档规则由根目录 `.gitattributes` 中的 `export-ignore` 定义；因此不会因为工作树
中存在未跟踪文件而把它们交付给客户。
