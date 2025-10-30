import logging
from typing import Iterable, List, Optional, Tuple

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
    allow_inner_outer_split: bool = False,
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
        ring_vertices_len = ring_num_hint * vertex_count
        allowed_lengths.add(ring_vertices_len)
        allowed_lengths.add(ring_vertices_len * 2)
    if allow_inner_outer_split:
        allowed_lengths.add(vertex_count * 2)

    use_inner_outer_split = False
    outer_radius_values: Optional[List[float]] = None

    if len(radius_values) == 1:
        radius_values = radius_values * vertex_count
    elif len(radius_values) not in allowed_lengths:
        raise ValueError(
            f"形状 '{shape_name}' 的倒角半径长度({len(radius_values)})不符合要求; 允许长度: {sorted(allowed_lengths | {1})}"
        )
    elif allow_inner_outer_split and len(radius_values) == vertex_count * 2:
        outer_radius_values = list(radius_values[vertex_count:])
        radius_values = list(radius_values[:vertex_count])
        use_inner_outer_split = True
    else:
        radius_values = list(radius_values)

    normalized_config["radius_list"] = radius_values
    if use_inner_outer_split:
        normalized_config["radius_outer_list"] = outer_radius_values
        normalized_config["radius_inner_outer_split"] = True
    else:
        normalized_config.pop("radius_outer_list", None)
        normalized_config.pop("radius_inner_outer_split", None)
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


def resolve_via_fillet_configs(
    shape_name: str,
    fillet_config: Optional[dict],
    base_radius_list: Optional[List[float]] = None,
    zoom_delta: Optional[float] = None,
) -> Tuple[Optional[dict], Optional[dict], Optional[dict]]:
    """根据 via 场景的半径配置拆分出适合 polygon2ring 使用的配置三元组。"""

    if not fillet_config or fillet_config.get("type") != "arc":
        return fillet_config, None, None

    base_config = dict(fillet_config)
    outer_list = base_config.get("radius_outer_list")
    split_flag = bool(base_config.get("radius_inner_outer_split") and outer_list)

    if split_flag:
        inner_list = base_config.get("radius_list")
        if inner_list is None:
            raise ValueError(f"形状 '{shape_name}' 的 via 倒角缺少 radius_list 配置")
        inner_config = dict(base_config)
        inner_config.pop("radius_outer_list", None)
        inner_config.pop("radius_inner_outer_split", None)
        inner_config["radius_list"] = list(inner_list)
        inner_config["preserve_radius_list"] = True

        outer_config = dict(inner_config)
        outer_config["radius_list"] = list(outer_list)
        outer_config["preserve_radius_list"] = True

        return None, inner_config, outer_config

    if "radius_outer_list" in base_config or "radius_inner_outer_split" in base_config:
        base_config.pop("radius_outer_list", None)
        base_config.pop("radius_inner_outer_split", None)

    via_radius_list = base_config.get("radius_list")
    if via_radius_list is not None:
        via_radius_list = list(via_radius_list)

    if (
        base_radius_list is not None
        and via_radius_list is not None
        and len(base_radius_list) == len(via_radius_list)
    ):
        if via_radius_list == base_radius_list:
            return base_config, None, None

        if zoom_delta is None:
            logger.warning(
                "形状 '%s' 的 via 检测到自定义倒角，但缺少 zoom_delta；保持原有自动行为。",
                shape_name,
            )
            return base_config, None, None

        if zoom_delta <= 0:
            raise ValueError(
                f"形状 '{shape_name}' 的 via 缩放差值(outer - inner = {zoom_delta}) 非正，无法生成外边界倒角"
            )

        inner_config = dict(base_config)
        inner_config["radius_list"] = via_radius_list
        inner_config["preserve_radius_list"] = True

        outer_config = dict(inner_config)
        outer_config["radius_list"] = [radius + zoom_delta for radius in via_radius_list]

        return None, inner_config, outer_config

    return base_config, None, None
