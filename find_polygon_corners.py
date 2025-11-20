#!/usr/bin/env python3
"""
Detect true polygon corners from a dense vertex list.

The script auto-detects polygon方向（顺/逆时针均可），输入首尾不重复（隐式闭合）。
输出的角索引会统一为逆时针编号（即若输入是顺时针，会自动镜像编号）。
它会在满足以下条件时标记为角点：
- The vertex is convex (relative to the provided ordering), and
- The interior angle is smaller than the provided threshold.

Usage examples:
  python find_polygon_corners.py "0,0; 1,0; 1,1; 0,1"
  python find_polygon_corners.py "[[0,0],[1,0],[1,1],[0,1]]"
  python find_polygon_corners.py --angle-threshold 150 --format json < vertices.txt
  python find_polygon_corners.py --file polygon.txt
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


Point = Tuple[float, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find true polygon corners by angle thresholding."
    )
    parser.add_argument(
        "vertices",
        nargs="?",
        help="顶点列表：支持 'x,y; x,y; ...' 字符串或 JSON 数组。若省略则从 stdin 读取。",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="包含顶点列表的文件，内容格式同位置参数（分号分隔或 JSON）。",
    )
    parser.add_argument(
        "--angle-threshold",
        type=float,
        default=170.0,
        help="Interior angle threshold in degrees. Convex vertices with an angle below this are treated as true corners. Default: 170.",
    )
    parser.add_argument(
        "--min-edge-length",
        type=float,
        default=1e-9,
        help="Ignore vertices where either adjacent edge is shorter than this value to avoid numerical noise. Default: 1e-9.",
    )
    parser.add_argument(
        "--format",
        choices=["plain", "json"],
        default="plain",
        help='Output format for indices: "plain" prints space-separated indices; "json" prints a JSON array. Default: plain.',
    )
    return parser.parse_args()


def normalize_vertices(raw: Iterable[Sequence[float]]) -> List[Point]:
    vertices: List[Point] = []
    for idx, point in enumerate(raw):
        if (
            not isinstance(point, Sequence)
            or len(point) != 2
            or any(not isinstance(c, (int, float)) for c in point)
        ):
            raise ValueError(f"Invalid vertex at index {idx}: {point!r}")
        vertices.append((float(point[0]), float(point[1])))
    if len(vertices) < 3:
        raise ValueError("At least three vertices are required.")
    return vertices


def parse_semicolon_vertices(text: str) -> List[Point]:
    tokens = [token.strip() for token in text.split(";")]
    vertices: List[Point] = []
    for idx, token in enumerate(token for token in tokens if token):
        parts = [p.strip() for p in token.split(",")]
        if len(parts) != 2:
            raise ValueError(f"Invalid 'x,y' pair at position {idx}: {token!r}")
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"Non-numeric coordinate at position {idx}: {token!r}") from exc
        vertices.append((x, y))
    if not vertices:
        raise ValueError("No vertices parsed from input.")
    return vertices


def parse_vertices_text(text: str) -> List[Point]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("No vertices provided.")
    if stripped[0] in {"[", "{"}:
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"无法解析 JSON 顶点列表: {exc}") from exc
        return normalize_vertices(raw)
    return normalize_vertices(parse_semicolon_vertices(stripped))


def load_vertices(args: argparse.Namespace) -> List[Point]:
    raw: Iterable[Sequence[float]]

    if args.file:
        text = args.file.read_text()
    elif args.vertices:
        text = args.vertices
    else:
        data = sys.stdin.read().strip()
        if not data:
            raise SystemExit("No vertices provided. Use an argument, --file, or stdin.")
        text = data

    return parse_vertices_text(text)


def angle_at(prev_pt: Point, curr_pt: Point, next_pt: Point) -> float:
    """Compute the interior angle at curr_pt in degrees (0-180)."""
    vec_in = (prev_pt[0] - curr_pt[0], prev_pt[1] - curr_pt[1])
    vec_out = (next_pt[0] - curr_pt[0], next_pt[1] - curr_pt[1])

    len_in = math.hypot(*vec_in)
    len_out = math.hypot(*vec_out)
    if len_in == 0.0 or len_out == 0.0:
        return math.nan

    dot = vec_in[0] * vec_out[0] + vec_in[1] * vec_out[1]
    cross = vec_out[0] * vec_in[1] - vec_out[1] * vec_in[0]
    # atan2 gives a stable small angle near collinear edges; result in [0, 180].
    return math.degrees(math.atan2(abs(cross), dot))


def find_corners(
        vertices: Sequence[Point],
        angle_threshold: float,
        min_edge_length: float = 0.0,
) -> List[int]:
    """Return indices of convex vertices whose interior angle is <= threshold."""
    n = len(vertices)
    if n < 3:
        return []

    # Signed area > 0 for CCW, < 0 for CW. Use sign to decide convexity direction.
    area2 = 0.0
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    if abs(area2) < 1e-12:
        orientation_sign = 1.0
        from_cw = False
    else:
        orientation_sign = 1.0 if area2 > 0 else -1.0
        from_cw = area2 < 0

    corners: List[int] = []
    for i in range(n):
        prev_pt = vertices[i - 1]
        curr_pt = vertices[i]
        next_pt = vertices[(i + 1) % n]

        vec_in = (prev_pt[0] - curr_pt[0], prev_pt[1] - curr_pt[1])
        vec_out = (next_pt[0] - curr_pt[0], next_pt[1] - curr_pt[1])
        len_in = math.hypot(*vec_in)
        len_out = math.hypot(*vec_out)
        if len_in < min_edge_length or len_out < min_edge_length:
            continue

        angle = angle_at(prev_pt, curr_pt, next_pt)
        if math.isnan(angle):
            continue

        # Convex check for CCW ordering: outgoing edge x incoming edge should be > 0.
        cross = vec_out[0] * vec_in[1] - vec_out[1] * vec_in[0]
        if cross * orientation_sign <= 0.0:
            continue

        if angle <= angle_threshold:
            corners.append(i)

    if from_cw:
        # 输入为顺时针，镜像索引到逆时针编号：i -> (n - 1 - i) % n。
        mirrored = [(n - 1 - i) % n for i in corners]
        corners = sorted(mirrored)

    return corners


def main() -> None:
    args = parse_args()
    vertices = load_vertices(args)
    indices = find_corners(
        vertices, angle_threshold=args.angle_threshold, min_edge_length=args.min_edge_length
    )

    if args.format == "json":
        json.dump(indices, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(" ".join(str(idx) for idx in indices) + "\n")


if __name__ == "__main__":
    main()
