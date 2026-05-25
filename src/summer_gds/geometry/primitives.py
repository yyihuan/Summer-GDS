from __future__ import annotations

import math

from summer_gds.model.protocol import Point

EPSILON = 1e-9


def signed_area(points: tuple[Point, ...]) -> float:
    area = 0.0
    for index, current in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += current.x * nxt.y - nxt.x * current.y
    return area / 2.0


def normalize_counterclockwise(points: tuple[Point, ...]) -> tuple[Point, ...]:
    if signed_area(points) < 0:
        return tuple(reversed(points))
    return points


def distance(left: Point, right: Point) -> float:
    return math.hypot(left.x - right.x, left.y - right.y)


def cross(a: Point, b: Point, c: Point) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def has_consecutive_duplicate_points(points: tuple[Point, ...]) -> bool:
    for index, point in enumerate(points):
        if points_equal(point, points[(index + 1) % len(points)]):
            return True
    return False


def points_equal(left: Point, right: Point) -> bool:
    return abs(left.x - right.x) <= EPSILON and abs(left.y - right.y) <= EPSILON


def is_simple_polygon(points: tuple[Point, ...]) -> bool:
    for left_index in range(len(points)):
        left_a = points[left_index]
        left_b = points[(left_index + 1) % len(points)]
        for right_index in range(left_index + 1, len(points)):
            if abs(left_index - right_index) == 1:
                continue
            if left_index == 0 and right_index == len(points) - 1:
                continue
            right_a = points[right_index]
            right_b = points[(right_index + 1) % len(points)]
            if segments_intersect(left_a, left_b, right_a, right_b):
                return False
    return True


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(a, c, b):
        return True
    if o2 == 0 and _on_segment(a, d, b):
        return True
    if o3 == 0 and _on_segment(c, a, d):
        return True
    if o4 == 0 and _on_segment(c, b, d):
        return True
    return False


def _orientation(a: Point, b: Point, c: Point) -> int:
    value = cross(a, b, c)
    if abs(value) <= EPSILON:
        return 0
    return 1 if value > 0 else -1


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return (
        min(a.x, c.x) - EPSILON <= b.x <= max(a.x, c.x) + EPSILON
        and min(a.y, c.y) - EPSILON <= b.y <= max(a.y, c.y) + EPSILON
        and abs(cross(a, b, c)) <= EPSILON
    )
