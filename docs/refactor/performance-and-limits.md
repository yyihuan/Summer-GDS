# Performance And Limits

## 1. 目标

第一版 refactor 不追求超大规模版图生成，但必须有明确上限，防止 CLI 卡死、内存暴涨或输出不可控 GDS/PNG。

性能策略：

- 默认安全上限。
- 错误优先于自动降级。
- 对 rings/via 的规模做显式限制。
- 所有上限后续可通过 benchmark 再放宽。

## 2. 默认限制

建议第一版限制：

| 项 | 默认上限 |
| --- | ---: |
| `shapes` 数量 | `200` |
| 单个 BoundaryObject 输入点数 | `10_000` |
| 单次 fillet 后点数 | `50_000` |
| 总输出 RegionObject 数量 | `1_000` |
| `rings.count` | `100` |
| 单个 ring boolean 后 polygon 数量 | `100` |
| 总 GDS polygon 数量 | `10_000` |
| PNG 最大像素边长 | `4096` |
| 单角圆弧采样点 | `512` |

超过限制应报错，不应静默截断。

## 3. 倒角精度限制

默认精度策略：

```text
radius <= 20um  -> precision = 0.001um
radius > 20um   -> precision = 0.01um
```

必须限制：

- `precision > 0`
- `precision >= dbu`
- 单角采样点数不超过上限

原因：

- 太小的 precision 会导致点数爆炸。
- 小于 dbu 的 precision 没有 GDS 网格意义。
- via/rings 会把倒角点数乘以 inner/outer 和 ring count。

## 4. Offset 风险

KLayout Region offset 可能产生：

- 空 Region。
- 多个外边界。
- 带洞 Region。
- 大量碎片。

第一版只允许 offset 后能转回单个 BoundaryObject 的情况继续倒角。

如果用户输入导致复杂结果，应报错：

```text
offset_multiple_boundaries
```

而不是自动挑选最大 polygon 或忽略洞。

## 5. Boolean 风险

via/rings 的 boolean 可能产生：

- 空 Region。
- 多 polygon。
- 带洞 Region。
- sliver。

第一版 output backend 可以写 RegionObject，但必须至少校验非空。

不在第一版做：

- sliver 清理。
- holes 精确分类。
- rings merge 后拓扑保证。

## 6. Rings 规模

rings 的输出规模约为：

```text
RegionObject count = rings.count
offset operations = rings.count * 2
fillet operations = rings.count * 2
boolean operations = rings.count
```

例如 `count=100`：

```text
200 offset
200 fillet
100 boolean
100 output regions
```

因此 rings 是第一版最容易放大计算量的对象。

建议：

- 默认 `rings.count <= 100`。
- 如果 GUI 允许更大值，应提示用户可能变慢。
- benchmark 通过后再提高上限。

## 7. Benchmark 场景

后续性能测试至少覆盖：

| benchmark | 目的 |
| --- | --- |
| `base_10k_vertices` | 单大 polygon。 |
| `base_offset_1k_vertices` | Region offset + boundary conversion。 |
| `via_1k_vertices` | inner/outer offset + boolean。 |
| `rings_count_100` | rings 放大效应。 |
| `mixed_200_shapes` | 多 shape 编排和 output backend 压力。 |
| `png_rings_count_100` | image renderer 在多 RegionObject 下的预览压力。 |

每个 benchmark 记录：

- parse time
- validation time
- geometry time
- output backend time
- peak memory
- output polygon count
- output file size

## 8. 性能预算

本地开发默认预算：

| 场景 | 目标 |
| --- | ---: |
| 小型 mixed fixture | `< 1s` |
| `rings.count=20` | `< 3s` |
| `rings.count=100` | `< 15s` |
| GDS writer smoke | `< 2s` |
| PNG renderer smoke | `< 2s` |

这些不是严格 SLA，而是回归警戒线。

如果一次改动让同一 fixture 慢 2 倍以上，应调查原因。

## 9. 可观测性

`export --debug-dir` 应输出阶段耗时：

```json
{
  "parse_ms": 12,
  "validate_ms": 4,
  "compile_ms": 6,
  "geometry_ms": 183,
  "output_ms": 41,
  "output_format": "png",
  "regions": 8,
  "polygons": 12
}
```

这可以帮助区分：

- YAML 慢。
- offset/boolean 慢。
- GDS writer 慢。
- image renderer 慢。

## 10. 后续优化方向

先不要做：

- 并行 executor。
- Region 缓存。
- 增量编译。
- 图形空间索引。

这些会增加复杂度。

第一版优先：

- 明确上限。
- 明确错误。
- 明确 benchmark。
- 用 KLayout 内置 Region 能力解决 offset/boolean。
