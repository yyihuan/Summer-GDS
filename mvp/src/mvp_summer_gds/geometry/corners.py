"""Corner-level geometry metadata for fillet strategies."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from mvp_summer_gds.geometry.primitives import EPSILON, cross
from mvp_summer_gds.model import Point


class CornerKind(str, Enum):
    CONVEX = "convex"
    CONCAVE = "concave"
    COLLINEAR = "collinear"


@dataclass(frozen=True)
class CornerContext:
    user_index: int
    normalized_index: int
    prev_point: Point
    vertex: Point
    next_point: Point
    incoming_edge: Point
    outgoing_edge: Point
    turn_sign: int
    corner_kind: CornerKind
    radius: float


@dataclass(frozen=True)
class ArcCornerPlan:
    context: CornerContext
    tangent_start: Point
    tangent_end: Point
    center: Optional[Point]
    sweep_direction: int
    segment_count: int
    output_points: List[Point]


def build_corner_contexts(points, radii=None, user_indices=None):
    count = len(points)
    if radii is None:
        radii = [0.0] * count
    if user_indices is None:
        user_indices = list(range(count))
    if len(radii) != count:
        raise ValueError("radii length must match point count.")
    if len(user_indices) != count:
        raise ValueError("user_indices length must match point count.")

    contexts = []
    for index, vertex in enumerate(points):
        prev_point = points[(index - 1) % count]
        next_point = points[(index + 1) % count]
        turn = cross(prev_point, vertex, next_point)
        turn_sign = _turn_sign(turn)
        contexts.append(
            CornerContext(
                user_index=user_indices[index],
                normalized_index=index,
                prev_point=prev_point,
                vertex=vertex,
                next_point=next_point,
                incoming_edge=Point(vertex.x - prev_point.x, vertex.y - prev_point.y),
                outgoing_edge=Point(next_point.x - vertex.x, next_point.y - vertex.y),
                turn_sign=turn_sign,
                corner_kind=_corner_kind(turn_sign),
                radius=float(radii[index]),
            )
        )
    return contexts


def _turn_sign(turn):
    if abs(turn) <= EPSILON:
        return 0
    return 1 if turn > 0 else -1


def _corner_kind(turn_sign):
    if turn_sign > 0:
        return CornerKind.CONVEX
    if turn_sign < 0:
        return CornerKind.CONCAVE
    return CornerKind.COLLINEAR
