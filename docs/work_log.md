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
- 阶段3：构建 Qt 主窗口（`QWebEngineView` + 底部 1/5 日志面板），集成生命周期与日志刷新；处理 `downloadRequested` 以恢复 GDS 下载，默认保存至 `downloads/`
