#!/usr/bin/env python3
"""
综合工具：读取原始坐标，检测真实角点，并生成三段输出。

输入文件格式：
- 每行一个顶点坐标，x 和 y 以空白或逗号分隔，例如：
    75.00000 181.06600
    104.10000,3023.20000
- 顶点顺序可以是顺时针或逆时针，首尾不重复（程序会自动闭合）。

输出：
1. 顶点列表（分号分隔，坐标格式为 `x,y`，每个数保留 3 位小数）。
2. “短格式”角控制列表：长度与顶点数量相同，真实角点标记为 50，其余为 0。
3. 加长控制列表：长度为 2N，前半部分全 0，后半部分与短格式对应但角点标记为 65。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

# 确保可以从仓库根目录导入 find_polygon_corners
import sys

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from find_polygon_corners import find_corners, parse_vertices_text

Point = Tuple[float, float]


def _normalize_line(line: str) -> str:
    tokens = [token for token in re.split(r"[,\s]+", line.strip()) if token]
    if len(tokens) != 2:
        raise ValueError(f"无法解析坐标行: {line!r}")
    x, y = float(tokens[0]), float(tokens[1])
    return f"{x},{y}"


def read_coordinate_file(path: Path) -> List[Point]:
    """读取文本坐标文件并按 find_polygon_corners 的格式解析。"""
    normalized_lines: List[str] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            normalized_lines.append(_normalize_line(stripped))

    if not normalized_lines:
        raise ValueError(f"文件 {path} 为空")

    # 将逐行坐标合并为 ';' 分隔的字符串复用原有解析逻辑。
    combined = ";".join(normalized_lines)
    return parse_vertices_text(combined)


def format_vertices(vertices: Sequence[Point]) -> str:
    return ";".join(f"{x:.3f},{y:.3f}" for x, y in vertices)


def make_control_list(count: int, corner_indices: Iterable[int], corner_value: int) -> List[int]:
    control = [0] * count
    for idx in corner_indices:
        control[idx] = corner_value
    return control


def process_file(
    path: Path,
    angle_threshold: float,
    min_edge_length: float,
    corner_value_short: int = 50,
    corner_value_long: int = 65,
) -> Tuple[str, List[int], List[int]]:
    vertices = read_coordinate_file(path)
    corners = find_corners(vertices, angle_threshold=angle_threshold, min_edge_length=min_edge_length)

    formatted_vertices = format_vertices(vertices)
    short_control = make_control_list(len(vertices), corners, corner_value_short)
    short_control_alt = make_control_list(len(vertices), corners, 10)
    short_control_alt2 = make_control_list(len(vertices), corners, 45)
    short_control_alt3 = make_control_list(len(vertices), corners, 65)
    long_control = [0] * len(vertices) + make_control_list(len(vertices), corners, corner_value_long)
    return formatted_vertices, short_control, short_control_alt, short_control_alt2, short_control_alt3, long_control


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成角点控制列表的工具脚本")
    parser.add_argument("file", type=Path, help="包含原始坐标的文本文件（每行一个 x,y）")
    parser.add_argument(
        "--angle-threshold",
        type=float,
        default=170.0,
        help="角判断阈值（°），默认 170",
    )
    parser.add_argument(
        "--min-edge-length",
        type=float,
        default=1e-9,
        help="忽略小于该长度的边（避免数值噪声），默认 1e-9",
    )
    parser.add_argument(
        "--format",
        choices=["plain", "json"],
        default="plain",
        help="控制列表输出格式：plain=方括号+逗号分隔，json=JSON 数组",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出文件路径；默认在输入文件同目录生成 *_processed.txt",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    formatted_vertices, short_control, short_control_alt, short_control_alt2, short_control_alt3, long_control = process_file(
        args.file,
        angle_threshold=args.angle_threshold,
        min_edge_length=args.min_edge_length,
    )

    def fmt_list(values: Sequence[int]) -> str:
        if args.format == "json":
            import json

            return json.dumps(values, ensure_ascii=False)
        return ",".join(str(v) for v in values)

    if args.output:
        output_path = args.output
    else:
        output_path = args.file.with_name(f"{args.file.stem}_processed.txt")

    lines = [
        ("顶点列表", formatted_vertices),
        ("短控制列表", fmt_list(short_control)),
        ("短控制列表2", fmt_list(short_control_alt2)),
        ("短控制列表3", fmt_list(short_control_alt)),
        ("短控制列表4", fmt_list(short_control_alt3)),
        ("加长控制列表", fmt_list(long_control)),
    ]

    joined = "\n".join(f"{title}:\n{value}" for title, value in lines)
    output_path.write_text(joined + "\n", encoding="utf-8")
    print(f"已写入: {output_path}")


if __name__ == "__main__":
    main()
