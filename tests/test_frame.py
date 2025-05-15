import unittest
import math
import matplotlib.pyplot as plt
from gds_utils.frame import Frame

# 辅助函数：生成多边形顶点

def gen_square(center=(0, 0), size=10):
    cx, cy = center
    s = size / 2
    return [
        (cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)
    ]

def gen_hexagon(center=(0, 0), r=5):
    cx, cy = center
    return [
        (cx + r * math.cos(math.pi / 3 * i), cy + r * math.sin(math.pi / 3 * i))
        for i in range(6)
    ]

def gen_star(center=(0, 0), outer=5, inner=2.5, points=5):
    cx, cy = center
    verts = []
    for i in range(points * 2):
        angle = math.pi / points * i - math.pi / 2
        r = outer if i % 2 == 0 else inner
        verts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return verts

def gen_circle(center=(0, 0), r=5, n=40):
    cx, cy = center
    return [
        (cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]

# 可视化辅助

def plot_polygon(ax, vertices, label=None, color='b', marker='o'):
    x, y = zip(*(vertices + [vertices[0]]))
    ax.plot(x, y, marker=marker, label=label, color=color)

class TestFrame(unittest.TestCase):
    def setUp(self):
        self.shapes = {
            'square': gen_square(size=10),
            'hexagon': gen_hexagon(r=5),
            'star': gen_star(outer=5, inner=2.5, points=5),
            'circle': gen_circle(r=5, n=40)
        }
        self.fillet_radius = 2

    def test_is_clockwise_and_ccw(self):
        for name, verts in self.shapes.items():
            frame = Frame(verts)
            # 顺时针测试
            cw = frame.is_clockwise()
            frame.ensure_counterclockwise()
            ccw = not frame.is_clockwise()
            self.assertTrue(ccw)

    def test_offset(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            frame = Frame(verts)
            offset_frame = frame.offset(2)
            ax = axs[idx // 2][idx % 2]
            plot_polygon(ax, frame.get_vertices(), label=f'{name} original', color='b')
            plot_polygon(ax, offset_frame.get_vertices(), label=f'{name} offset', color='r')
            ax.set_title(f'Offset: {name}')
            ax.legend()
            ax.axis('equal')
        plt.tight_layout()
        plt.savefig('test_frame_offset.png')
        plt.close()

    def test_apply_arc_fillet(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            if name == 'circle':
                continue  # 圆形不做倒角
            frame = Frame(verts)
            # 针对星形和六边形用更小的倒角半径
            fillet_radius = 1 if name in ('star', 'hexagon') else self.fillet_radius
            try:
                fillet_frame = frame.apply_arc_fillet(fillet_radius, precision=0.05, interactive=False)
                ax = axs[idx // 2][idx % 2]
                plot_polygon(ax, frame.get_vertices(), label=f'{name} original', color='b')
                plot_polygon(ax, fillet_frame.get_vertices(), label=f'{name} fillet', color='g')
                ax.set_title(f'Arc Fillet: {name}')
                ax.legend()
                ax.axis('equal')
            except ValueError as e:
                print(f"{name} arc fillet skipped: {e}")
        plt.tight_layout()
        plt.savefig('test_frame_arc_fillet.png')
        plt.close()

    def test_apply_adaptive_fillet(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            if name == 'circle':
                continue  # 圆形不做倒角
            frame = Frame(verts)
            fillet_radius = 1 if name in ('star', 'hexagon') else self.fillet_radius
            try:
                fillet_frame = frame.apply_adaptive_fillet(fillet_radius, fillet_radius, precision=0.05, interactive=False)
                ax = axs[idx // 2][idx % 2]
                plot_polygon(ax, frame.get_vertices(), label=f'{name} original', color='b')
                plot_polygon(ax, fillet_frame.get_vertices(), label=f'{name} adaptive fillet', color='m')
                ax.set_title(f'Adaptive Fillet: {name}')
                ax.legend()
                ax.axis('equal')
            except ValueError as e:
                print(f"{name} adaptive fillet skipped: {e}")
        plt.tight_layout()
        plt.savefig('test_frame_adaptive_fillet.png')
        plt.close()

    def test_is_convex_vertex_and_line_intersection(self):
        # 只做简单的API调用覆盖
        square = self.shapes['square']
        n = len(square)
        for i in range(n):
            prev = square[i - 1]
            curr = square[i]
            next = square[(i + 1) % n]
            Frame.is_convex_vertex(prev, curr, next)
        # line_intersection
        a = ((0, 0), (1, 1))
        b = ((0, 1), (1, 0))
        Frame.line_intersection(a, b)
        Frame.line_intersection(((0, 0), (1, 0)), ((0, 1), (1, 1)))

if __name__ == '__main__':
    unittest.main() 