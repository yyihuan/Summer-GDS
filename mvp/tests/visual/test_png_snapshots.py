from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch

from mvp_summer_gds.config.loader import load_yaml_file
from mvp_summer_gds.config.schema import normalize_config
from mvp_summer_gds.geometry.renderer import render_config

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
VISUAL_OUTPUT = Path(__file__).resolve().parents[1] / "_visual_output"


def test_visual_png_snapshots_are_generated_for_valid_shapes():
    outputs = [
        _render_fixture_png("valid_polygon.yaml", "valid_polygon.png"),
        _render_fixture_png("valid_polygon_arc.yaml", "valid_polygon_arc.png"),
        _render_fixture_png("valid_polygon_arc_mixed.yaml", "valid_polygon_arc_mixed.png"),
        _render_fixture_png(
            "valid_polygon_arc_sharp_convex.yaml",
            "valid_polygon_arc_sharp_convex.png",
        ),
        _render_fixture_png("valid_polygon_arc_arrow_concave.yaml", "valid_polygon_arc_arrow_concave.png"),
        _render_fixture_png("valid_polygon_arc_star_concave.yaml", "valid_polygon_arc_star_concave.png"),
        _render_fixture_png("valid_polygon_arc_octagon_um.yaml", "valid_polygon_arc_octagon_um.png"),
        _render_fixture_png("valid_polygon_arc_octagon_scaled.yaml", "valid_polygon_arc_octagon_scaled.png"),
        _render_fixture_png("valid_circle.yaml", "valid_circle.png"),
    ]

    for output in outputs:
        assert output.exists()
        assert output.stat().st_size > 1_000


def test_dense_arc_points_are_not_annotated_as_individual_vertices():
    class FakeAxes:
        def __init__(self):
            self.plot_calls = 0
            self.text_calls = 0

        def plot(self, *args, **kwargs):
            self.plot_calls += 1

        def text(self, *args, **kwargs):
            self.text_calls += 1

    axes = FakeAxes()
    dense_points = [(float(index), 0.0) for index in range(17)]

    _annotate_vertices(axes, dense_points)

    assert axes.plot_calls == 0
    assert axes.text_calls == 0


def _render_fixture_png(fixture_name, output_name):
    config = normalize_config(load_yaml_file(FIXTURES / fixture_name))
    polygons = render_config(config)
    output = VISUAL_OUTPUT / output_name
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6), dpi=160)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(fixture_name)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, color="#d8dde3", linewidth=0.6)

    for polygon in polygons:
        points = [(point.x, point.y) for point in polygon.points]
        patch = PolygonPatch(
            points,
            closed=True,
            facecolor="#5fa8d3",
            edgecolor="#0b3954",
            linewidth=1.5,
            alpha=0.65,
        )
        ax.add_patch(patch)
        _annotate_vertices(ax, points)

    _fit_axes(ax, polygons)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)
    return output


def _annotate_vertices(ax, points):
    if len(points) > 16:
        return
    for index, (x_coord, y_coord) in enumerate(points):
        ax.plot(x_coord, y_coord, marker="o", markersize=2.5, color="#0b3954")
        ax.text(x_coord, y_coord, str(index), fontsize=6, color="#1f2933")


def _fit_axes(ax, polygons):
    xs = [point.x for polygon in polygons for point in polygon.points]
    ys = [point.y for polygon in polygons for point in polygon.points]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    pad = max(x_span, y_span, 1.0) * 0.12
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
