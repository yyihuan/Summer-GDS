# Summer-GDS Refactor Docs

文档版本：v2.2
日期：2026-05-25
状态：完整产品架构规划

---

## 文档分区

```text
docs/refactor/
├── product/       # 产品边界、用户能力、MVP 历史
├── contracts/     # YAML 和 CLI/app service 契约
├── architecture/  # 程序结构、数据模型、处理流水线
├── quality/       # 校验、测试、性能、专项倒角测试
├── frontend/      # GUI 架构、交互、HTML/CSS 设计系统
└── planning/      # 实施路线
```

## 推荐阅读顺序

1. [PRD](./product/PRD.md)
   产品边界、用户目标、GUI 产物范围。

2. [技术规格总览](./architecture/technical-spec.md)
   已锁定决策、模块边界和文档导航。

3. [YAML v2 协议](./contracts/yaml-protocol.md)
   GUI、CLI、agent 共享的正式配置协议。

4. [CLI 契约](./contracts/cli-contract.md)
   CLI 命令、退出码、app service 和 GUI 调用约定。

5. [程序架构](./architecture/architecture.md)
   CLI-first 架构、模块边界、依赖方向。

6. [处理流水线](./architecture/processing-pipeline.md)
   `base_shape`、`rings`、`via` 如何统一走 Boundary/Region 流水线。

7. [数据模型](./architecture/data-model.md)
   `sid`、`cid`、BoundaryObject、RegionObject、ShapeResult 等内部对象。

8. [校验与错误模型](./quality/validation-and-errors.md)
   最低校验、错误码、错误路径格式。

9. [测试策略](./quality/testing-strategy.md)
   单元测试、集成测试、GDS smoke 和 image renderer 预览测试矩阵。

10. [性能与限制](./quality/performance-and-limits.md)
    默认上限、benchmark 场景、rings/via 规模风险。

11. [前端技术架构](./frontend/frontend-architecture.md)
    GUI 技术选型、API、安全边界、部署入口。

12. [前端部署与打包](./frontend/deployment.md)
    不同平台的直接启动方式、单文件打包方式。

13. [前端交互与页面设计](./frontend/frontend-interaction-design.md)
    页面布局、组件设计、交互流程、模态框设计。

14. [前端设计系统](./frontend/frontend-design-system.md)
    HTML/CSS tokens、语义 DOM 骨架、组件 class 和状态属性。

15. [倒角测试设计](./quality/fillet-test-design.md)
    倒角算法和可视化测试的专项设计。

16. [实施路线](./planning/implementation-roadmap.md)
    后续开发阶段、每阶段目标、验收标准。

17. [MVP Plan Archive](./product/MVP_PLAN.md)
    历史参考，不作为当前执行依据。

---

## 核心结论

- GUI 负责生成 YAML，CLI/app service 是稳定执行入口。
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

## 当前 MVP 与完整产品的关系

当前 `mvp/` 已完成：

- `base_shape` polygon/circle。
- polygon 圆弧倒角。
- CLI validate/generate。
- GDS 测试产物和 image renderer 预览测试。
- KLayout-backed GDS writer。

完整产品在此基础上增加：

- YAML v2 的 `sid` / `name` / `source`。
- `base_shape.source.ref + offset`。
- `rings`。
- `via`。
- BoundaryObject / RegionObject 流水线。
- KLayout Region offset / boolean。
- output backend 统一接受 RegionObject。
