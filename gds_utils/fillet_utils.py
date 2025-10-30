import logging
from typing import Iterable, List, Optional

logger = logging.getLogger("gds_utils")


def _ensure_float_list(values: object, *, label: str) -> List[float]:
    if isinstance(values, (int, float)):
        return [float(values)]

    if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        floats: List[float] = []
        for idx, item in enumerate(values):
            if not isinstance(item, (int, float)):
                raise ValueError(f"{label} 第 {idx} 个元素类型无效: {type(item)}")
            floats.append(float(item))
        return floats

    raise ValueError(f"{label} 类型无效: {type(values)}")


def normalize_arc_fillet_config(
    shape_name: str,
    fillet_config: Optional[dict],
    vertex_count: int,
    ring_num_hint: Optional[int] = None,
) -> Optional[dict]:
    if not fillet_config or fillet_config.get("type") != "arc":
        return fillet_config

    if vertex_count <= 0:
        raise ValueError(f"形状 '{shape_name}' 的顶点数量非法: {vertex_count}")

    normalized_config = dict(fillet_config)

    if "radius_list" in normalized_config:
        raw_radius_list = normalized_config["radius_list"]
    elif "radii" in normalized_config:
        raw_radius_list = normalized_config["radii"]
    elif "radius" in normalized_config:
        raw_radius_list = normalized_config["radius"]
    else:
        raise ValueError(f"形状 '{shape_name}' 的圆弧倒角缺少 radius 或 radius_list 配置")

    radius_values = _ensure_float_list(raw_radius_list, label=f"形状 '{shape_name}' 的倒角半径")
    if not radius_values:
        raise ValueError(f"形状 '{shape_name}' 的倒角半径列表为空")

    allowed_lengths = {vertex_count}
    if ring_num_hint and isinstance(ring_num_hint, int) and ring_num_hint > 0:
        allowed_lengths.add(ring_num_hint * vertex_count)

    if len(radius_values) == 1:
        radius_values = radius_values * vertex_count
    elif len(radius_values) not in allowed_lengths:
        raise ValueError(
            f"形状 '{shape_name}' 的倒角半径长度({len(radius_values)})不符合要求; 允许长度: {sorted(allowed_lengths | {1})}"
        )

    normalized_config["radius_list"] = radius_values
    normalized_config.pop("radius", None)
    normalized_config.pop("radii", None)

    logger.debug(
        "规范化倒角配置: shape=%s, vertices=%d, ring_num_hint=%s, radius_len=%d",
        shape_name,
        vertex_count,
        ring_num_hint,
        len(radius_values),
    )
    return normalized_config
