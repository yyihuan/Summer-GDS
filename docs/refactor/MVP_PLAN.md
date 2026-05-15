# MVP Plan Archive

## 1. 状态

文档版本：v2.0 archive
日期：2026-05-16
状态：历史参考

原 MVP 已完成：

- CLI validate/generate。
- YAML v1 基础解析。
- `base_shape` polygon/circle。
- polygon 圆弧倒角。
- KLayout-backed GDS 输出。
- pytest 回归测试。

后续开发不再以本文件作为执行依据。

## 2. 新执行依据

完整产品 refactor 以以下文档为准：

- [PRD](./PRD.md)
- [技术规格总览](./technical-spec.md)
- [YAML v2 协议](./yaml-protocol.md)
- [程序架构](./architecture.md)
- [处理流水线](./processing-pipeline.md)
- [数据模型](./data-model.md)
- [校验与错误模型](./validation-and-errors.md)
- [测试策略](./testing-strategy.md)
- [实施路线](./implementation-roadmap.md)

## 3. MVP 与 v2 的关系

| 主题 | MVP | v2 refactor |
| --- | --- | --- |
| 输入协议 | YAML v1 | YAML v2 |
| shape id | 旧协议字段 | `sid` 整数，全局唯一 |
| 引用 | 不支持正式 source ref | `source.ref` 引用前序 `sid` |
| offset | 非主线能力 | 使用 KLayout Region offset |
| boolean | 非主线能力 | 使用 KLayout Region boolean |
| output backend 输入 | polygon / 当前实现对象 | 只接受 RegionObject |
| rings/via | 不支持 | 正式支持 |

## 4. 迁移原则

- 不在主 parser 中长期混合 v1/v2。
- 如需兼容旧文件，应写独立 migrator。
- 当前 MVP 中可复用的圆弧倒角能力应迁移为 `BoundaryObject -> BoundaryObject`。
- 当前 GDS writer 应改造成 Region-only output backend，并新增同级 image renderer。
- 当前测试 fixture 可保留为 legacy 测试，但新功能必须使用 YAML v2 fixture。
