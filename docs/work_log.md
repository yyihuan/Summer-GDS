# 工作日志

## 2024-10-14 缩放覆盖问题（提交 0dd31a4）
- 修复派生图形缩放字段在用户覆写后仍被继承值回滚的问题
- 在 `LinkageOverrideManager` 中记录覆写并优先填充覆写值，保障缩放字段可独立编辑

## 2024-10-15 环阵列与圆形属性联动优化（当前）
- 调整继承链，确保环宽/环距/环数以及圆形元数据在 UI 中实时同步
- 修复派生侧覆写被继承值覆盖的问题，覆盖后徽章状态与 YAML 输出保持一致
- 添加调试脚本 `runRingsInheritanceDebugScenario`、`runCircleInheritanceDebugScenario` 协助验证

## 2024-10-16 圆形精度范围扩展
- 放宽圆形精度（segments）输入范围至 3-512，可用于生成任意正多边形
- 同步更新前端表单、算法校验以及相关文档，将旋转角度作为后续增强目标

## 2025-10-18 Qt 桌面入口阶段推进
- 阶段1：新增 `web_gui.qt_launcher` Python 启动器，统一处理参数解析、配置合并与 `--headless` 路径；保留 shell 脚本作为兼容入口
- 阶段2：实现 `ServerWorker`（基于 `werkzeug.make_server`）与 `LogBridge`，支持服务线程化、日志桥接，并补充 CLI/单元测试
- 阶段3：构建 Qt 主窗口（`QWebEngineView` + 底部 1/5 日志面板），集成生命周期与日志刷新；处理 `downloadRequested`，支持用户自选下载路径并记住历史；成功仅弹窗告知，日志面板仅记录取消/异常

## 2025-10-19 环阵列独立缩放改造
- CLI 侧 (`main.py`) 支持 `inner_zoom`/`outer_zoom` 两个 rings 专用参数；若未提供仍沿用旧 `zoom` 值，保持现有 YAML 兼容性。
- `Region.create_rings` 重构为逐环调用 `polygon2ring`，统一展开环宽/环距序列，允许独立控制内外缩放，同时保留对老版 `zoom` 补偿公式的兼容。
- 新增 `tests/test_region.py::test_create_rings_independent_zoom` 与 `test_create_rings_zoom_compatibility` 校验内外缩放及向后兼容行为（需在具备 KLayout 运行环境的宿主机执行，沙箱内仍会因 Signal 11 失败）。

## 2025-10-20 环阵列倒角模式与半径解析强化
- 解析阶段统一改用 `fillet.radius_list`，单值 `radius` 会自动展开；长度不匹配、出现负值等异常时立即抛错，避免生成非法几何。
- 新增 rings `ring_mode`（`custom` / `concentric`）并通过 `build_ring_radius_series` 生成逐环倒角列表，`Region.create_rings` 可按圈覆盖 `radius_list`，同时兼容旧配置。
- 补充 `tests/test_fillet_radius_parsing.py`、`tests/test_ring_radius_series.py` 展示输入/输出快照；新增 `region_applies_series` 用例验证按圈覆盖逻辑。
- 新增示例 `examples/rings_fillet_modes.yaml`，并更新 `docs/region.md`、`docs/fillet_radius_list.md` 说明严格校验与两种模式的用法。

## 2025-10-30 环阵列 GUI 更新
- rings 卡片新增 ring_mode 下拉以及 inner/outer 独立缩放输入，默认值 0，保持与 CLI 参数一致。
- 修正 polygon 卡片布局被误改的问题，确保仅 rings 模板包含环特有配置。
- README 与示例说明补充环模式与倒角半径列表长度规则，帮助前端操作与 YAML 输出来回映射。
