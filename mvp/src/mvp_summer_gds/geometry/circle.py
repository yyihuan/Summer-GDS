"""Circle approximation for MVP GDS output."""

import math

from mvp_summer_gds.model import Point

DEFAULT_CIRCLE_SEGMENTS = 128


def approximate_circle(center, radius, segments=DEFAULT_CIRCLE_SEGMENTS):
    if segments < 3:
        raise ValueError("circle approximation needs at least 3 segments.")
    points = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        points.append(
            Point(
                x=center.x + radius * math.cos(angle),
                y=center.y + radius * math.sin(angle),
            )
        )
    return points
