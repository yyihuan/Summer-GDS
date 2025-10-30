# 环阵列倒角模式改造实施计划

目标：统一倒角半径表示方式，新增 `custom`（默认）与 `concentric` 两种模式，并在配置异常（长度不匹配等）时立即报错终止，保证行为可预期。

## 阶段 1：半径配置解析重构
- **内容**
  - 调整 `main.py` 中 `fillet` 解析逻辑，统一使用 `radius_list`；若仅提供 `radius`，扩展为与顶点数相同的列表。
  - 在 rings 分支新增 `ring_mode` 读取（默认 `custom`），长度不匹配、为空等情况直接抛出异常并终止。
- **验证**
  - 编写/更新单元测试覆盖：`radius` → 扩展列表；`radius_list` 长度正确/错误时的行为（错误需断言抛异常）。

## 阶段 2：半径序列生成工具函数
- **内容**
  - 实现 `_build_ring_radius_series(mode, base_radius_list, ring_width_list, ring_space_list, zoom_params, ring_num)`，输出二维列表。
  - `custom`：严格校验长度（必须为 `ring_num * vertex_count` 或 `vertex_count`），否则抛异常。
  - `concentric`：基于偏移累积计算每圈半径，保持同心；若无法满足（如负值等），同样抛异常。
- **验证**
  - 新增单元测试：`custom`（匹配长度/不匹配）、`concentric`（检查输出半径与理论值）；构造错误输入确保异常抛出。

## 阶段 3：Region.create_rings 适配
- **内容**
  - 调整 `Region.create_rings` 签名/内部逻辑，接受 `ring_radii_series` 并逐圈复用；`fillet_config` 从原值克隆后覆盖 `radius_list`。
  - 对 `adaptive` 类型保持兼容，必要时限制或抛错（若暂不支持列表形式）。
- **验证**
  - 单测：`custom` 与 `concentric` 模式生成结果是否符合预期（例如比较布尔差或检查倒角计数）。
  - 旧配置（无 `ring_mode`）应与改造前输出一致。

## 阶段 4：示例与文档
- **内容**
  - 新增 `examples/rings_fillet_modes.yaml` 展示两种模式。
  - 更新 `docs/region.md`、`docs/work_log.md` 说明倒角模式及严格校验规则。
- **验证**
  - 运行示例 YAML，确认程序在正常/错误输入时行为符合预期；文档经人工检查。
