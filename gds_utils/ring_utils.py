import logging
from typing import Iterable, List

logger = logging.getLogger("gds_utils")


def _ensure_float_sequence(values: object, label: str) -> List[float]:
    if isinstance(values, (int, float)):
        return [float(values)]

    if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        result: List[float] = []
        for idx, item in enumerate(values):
            if not isinstance(item, (int, float)):
                raise ValueError(f"{label} 第 {idx} 个元素类型无效: {type(item)}")
            result.append(float(item))
        return result

    raise ValueError(f"{label} 类型无效: {type(values)}")


def _expand_ring_sequence(raw_value: object, expected_len: int, label: str) -> List[float]:
    seq = _ensure_float_sequence(raw_value, label)
    if len(seq) == 1 and expected_len > 1:
        seq = seq * expected_len
    if len(seq) != expected_len:
        raise ValueError(f"{label} 长度({len(seq)})与预期({expected_len})不匹配")
    return seq


def build_ring_radius_series(
    mode: str,
    base_radius_list: object,
    ring_width_list: object,
    ring_space_list: object,
    zoom_params: dict,
    ring_num: int,
) -> List[List[float]]:
    if not isinstance(ring_num, int) or ring_num <= 0:
        raise ValueError(f"ring_num 必须为正整数，当前值: {ring_num}")

    vertex_count = zoom_params.get("vertex_count")
    if not isinstance(vertex_count, int) or vertex_count <= 0:
        raise ValueError(f"vertex_count 必须为正整数，当前值: {vertex_count}")

    normalized_mode = (mode or "custom").lower()
    if normalized_mode not in {"custom", "concentric"}:
        raise ValueError(f"不支持的 ring_mode: {mode}")

    width_seq = _expand_ring_sequence(ring_width_list, ring_num, "ring_width_list")
    space_seq = _expand_ring_sequence(ring_space_list, ring_num, "ring_space_list")

    if any(width <= 0 for width in width_seq):
        raise ValueError(f"ring_width_list 存在非正值: {width_seq}")
    if any(space < 0 for space in space_seq):
        raise ValueError(f"ring_space_list 存在负值: {space_seq}")

    base_zoom = float(zoom_params.get("base_zoom", 0.0) or 0.0)
    inner_adjust = float(zoom_params.get("inner_adjust", 0.0) or 0.0)
    outer_adjust = float(zoom_params.get("outer_adjust", 0.0) or 0.0)

    offsets: List[tuple[float, float]] = []
    offset_accumulator = 0.0
    for idx in range(ring_num):
        baseline_inner = offset_accumulator - base_zoom
        baseline_outer = baseline_inner + width_seq[idx]
        inner_offset = baseline_inner + inner_adjust
        outer_offset = baseline_outer + outer_adjust
        if outer_offset <= inner_offset:
            raise ValueError(
                f"环 {idx} 的外边界偏移({outer_offset}) 不大于内边界({inner_offset})"
            )
        offsets.append((inner_offset, outer_offset))
        offset_accumulator += width_seq[idx] + space_seq[idx]

    flat_radii = _ensure_float_sequence(base_radius_list, "base_radius_list")
    ring_series: List[List[float]]

    if normalized_mode == "custom":
        if len(flat_radii) == vertex_count:
            ring_series = [flat_radii[:] for _ in range(ring_num)]
        elif len(flat_radii) == ring_num * vertex_count:
            ring_series = [
                [float(val) for val in flat_radii[i * vertex_count:(i + 1) * vertex_count]]
                for i in range(ring_num)
            ]
        else:
            raise ValueError(
                f"custom 模式的半径长度({len(flat_radii)})与顶点数({vertex_count})或"
                f" ring_num*vertex_count({ring_num * vertex_count}) 不匹配"
            )
    else:
        if len(flat_radii) == 1 and vertex_count > 1:
            flat_radii = flat_radii * vertex_count
        if len(flat_radii) != vertex_count:
            raise ValueError(
                f"concentric 模式需要 {vertex_count} 个半径值，当前长度: {len(flat_radii)}"
            )
        ring_series = [flat_radii[:] for _ in range(ring_num)]

    for idx, radii in enumerate(ring_series):
        if len(radii) != vertex_count:
            raise ValueError(
                f"环 {idx} 的半径列表长度({len(radii)})与顶点数({vertex_count})不符"
            )
        if any(radius < 0 for radius in radii):
            raise ValueError(f"环 {idx} 的半径列表存在负值: {radii}")

    logger.debug(
        "ring_mode=%s, ring_num=%d, vertex_count=%d, offsets=%s",
        normalized_mode,
        ring_num,
        vertex_count,
        offsets,
    )
    return ring_series
