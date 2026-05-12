"""Small polygon helpers used by the MVP validator.

The MVP keeps these helpers dependency-free so YAML validation can run without
KLayout. GDS writing is the only layer that imports KLayout.
"""

import math

from mvp_summer_gds.model import Point

EPSILON = 1e-9


def is_finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def points_equal(a, b, epsilon=EPSILON):
    return abs(a.x - b.x) <= epsilon and abs(a.y - b.y) <= epsilon


def signed_area(points):
    area = 0.0
    count = len(points)
    for index in range(count):
        current = points[index]
        nxt = points[(index + 1) % count]
        area += current.x * nxt.y
        area -= nxt.x * current.y
    return area / 2.0


def is_clockwise(points):
    return signed_area(points) < 0


def normalize_counterclockwise(points):
    if is_clockwise(points):
        return list(reversed(points)), True
    return list(points), False


def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def cross(a, b, c):
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def has_duplicate_points(points):
    for left_index in range(len(points)):
        for right_index in range(left_index + 1, len(points)):
            if points_equal(points[left_index], points[right_index]):
                return True
    return False


def has_consecutive_duplicate_points(points):
    for index in range(len(points)):
        if points_equal(points[index], points[(index + 1) % len(points)]):
            return True
    return False


def _orientation(a, b, c):
    value = cross(a, b, c)
    if abs(value) <= EPSILON:
        return 0
    return 1 if value > 0 else -1


def _on_segment(a, b, c):
    return (
        min(a.x, c.x) - EPSILON <= b.x <= max(a.x, c.x) + EPSILON
        and min(a.y, c.y) - EPSILON <= b.y <= max(a.y, c.y) + EPSILON
        and abs(cross(a, b, c)) <= EPSILON
    )


def segments_intersect(a, b, c, d):
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


def is_simple_polygon(points):
    count = len(points)
    for left_index in range(count):
        left_a = points[left_index]
        left_b = points[(left_index + 1) % count]
        for right_index in range(left_index + 1, count):
            if abs(left_index - right_index) == 1:
                continue
            if left_index == 0 and right_index == count - 1:
                continue
            right_a = points[right_index]
            right_b = points[(right_index + 1) % count]
            if segments_intersect(left_a, left_b, right_a, right_b):
                return False
    return True


def is_convex_polygon(points):
    sign = 0
    count = len(points)
    for index in range(count):
        turn = cross(points[index], points[(index + 1) % count], points[(index + 2) % count])
        if abs(turn) <= EPSILON:
            continue
        turn_sign = 1 if turn > 0 else -1
        if sign == 0:
            sign = turn_sign
        elif sign != turn_sign:
            return False
    return sign != 0
