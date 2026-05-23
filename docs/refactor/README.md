# Summer-GDS Refactor Docs

文档版本：v2.0
日期：2026-05-16
状态：完整产品架构规划

---

## 阅读顺序

1. [PRD](./PRD.md)
   产品边界、用户目标、当前 MVP 与完整产品的关系。

2. [技术规格总览](./technical-spec.md)
   完整产品的关键决策、模块清单、开发原则和文档导航。

3. [YAML v2 协议](./yaml-protocol.md)
   GUI 与 CLI 之间的正式配置协议。

4. [CLI 契约](./cli-contract.md)
   CLI 命令、退出码、debug 输出和 GUI 调用约定。

5. [程序架构](./architecture.md)
   CLI-first 架构、模块边界、依赖方向、Mermaid 图。

6. [处理流水线](./processing-pipeline.md)
   `base_shape`、`rings`、`via` 如何统一走 Boundary/Region 流水线。

7. [数据模型](./data-model.md)
   `sid`、`cid`、BoundaryObject、RegionObject、ShapeResult 等内部对象。

8. [校验与错误模型](./validation-and-errors.md)
   必须做的最低限度校验、错误码、错误路径格式。

9. [测试策略](./testing-strategy.md)
   单元测试、集成测试、GDS smoke 和 image renderer 预览测试矩阵。

10. [性能与限制](./performance-and-limits.md)
    默认上限、benchmark 场景、rings/via 规模风险。

11. [实施路线](./implementation-roadmap.md)
   后续开发阶段、每阶段目标、验收标准、并行开发策略。

12. [倒角测试设计](./fillet-test-design.md)
    倒角算法和可视化测试的专项设计。

13. [前端技术架构](./frontend-architecture.md)
    GUI 技术选型、项目结构、API 设计、Windows 打包方案。

14. [前端交互与页面设计](./frontend-interaction-design.md)
    页面布局、组件设计、交互流程、模态框设计。

15. [前端设计系统](./frontend-design-system.md)
    HTML/CSS tokens、语义 DOM 骨架、组件 class 和状态属性。

---

## 核心结论

- GUI 负责生成 YAML，CLI 是唯一稳定执行入口。
- YAML 中声明的每个 `shape` 都是公开输出对象。
- 内部临时对象如 inner/outer 不进入 YAML。
- `base_shape`、`rings`、`via` 共用同一套 Boundary/Region 流水线。
- offset 必须发生在倒角前。
- boolean 必须发生在倒角后。
- GDS writer 和 image renderer 都只接受 RegionObject。
- GUI 用户产物只有 YAML 和 GDS；SVG 只作为程序内部实时预览。
- image renderer 是标准 backend，用于 SVG 预览、CI 和开发诊断；PNG 不作为 GUI 产品功能。
- 前端第一版使用本地 HTML/CSS/JS 和 CSS variables，不使用 CDN、Tailwind、Bootstrap 或 npm build chain。
- `validate` 只做协议级预检，backend 校验使用 `export --dry-run --format ...`。
- 输出路径由 CLI/app service 统一解析，默认不覆盖，正式写出使用 atomic rename。
- 第一版不做复杂拓扑分类，但必须做流水线前置条件校验。

---

## 当前 MVP 与完整产品的关系

当前 `mvp/` 已完成：

- `base_shape` polygon/circle
- polygon 圆弧倒角
- CLI validate/generate
- GDS 测试产物和 image renderer 预览测试
- KLayout-backed GDS writer

完整产品在此基础上增加：

- YAML v2 的 `sid` / `name` / `source`
- `base_shape.source.ref + offset`
- `rings`
- `via`
- BoundaryObject / RegionObject 流水线
- KLayout Region offset / boolean
- output backend 统一接受 RegionObject
