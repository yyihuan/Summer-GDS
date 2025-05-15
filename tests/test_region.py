from gds_utils.utils import setup_logging
setup_logging(show_log=True)

import unittest
import math
import matplotlib.pyplot as plt
from gds_utils.frame import Frame
from gds_utils.region import Region

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

def gen_circle(center=(0, 0), r=5, n=256):
    cx, cy = center
    return [
        (cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]

# 可视化辅助

def plot_region(ax, region, label=None, color='b'):
    # region.kdb_region是KLayout Region对象，直接用polygon点画
    polygons = region.kdb_region.each()
    for poly in polygons:
        # 直接对poly调用each_point_hull()
        pts = [(pt.x, pt.y) for pt in poly.each_point_hull()]
        if len(pts) > 0:
            x, y = zip(*(pts + [pts[0]]))
            ax.plot(x, y, label=label, color=color)
            label = None  # 只加一次label

class TestRegion(unittest.TestCase):
    def setUp(self):
        self.shapes = {
            'square': gen_square(size=10),
            'hexagon': gen_hexagon(r=5),
            'star': gen_star(outer=5, inner=2.5, points=5),
            'circle': gen_circle(r=5, n=256)
        }

    def test_create_polygon(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            frame = Frame(verts)
            region = Region.create_polygon(frame)
            ax = axs[idx // 2][idx % 2]
            plot_region(ax, region, label=f'{name} region', color='g')
            ax.set_title(f'Region Polygon: {name}')
            ax.legend()
            ax.axis('equal')
            self.assertFalse(region.kdb_region.is_empty())
        plt.tight_layout()
        plt.savefig('test_region_polygon.png')
        plt.close()

    def test_create_rings(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            frame = Frame(verts)
            region = Region.create_rings(frame, ring_width=3, ring_space=5, ring_num=3)
            ax = axs[idx // 2][idx % 2]
            plot_region(ax, region, label=f'{name} rings', color='m')
            ax.set_title(f'Region Rings: {name}')
            ax.legend()
            ax.axis('equal')
            self.assertFalse(region.kdb_region.is_empty())
        plt.tight_layout()
        plt.savefig('test_region_rings.png')
        plt.close()

    def test_create_polygon_fillet(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            frame = Frame(verts)
            if name == 'circle':
                region = Region.create_polygon(frame)  # 圆形不做倒角
            else:
                fillet_radius = 1 if name in ('star', 'hexagon') else 2
                fillet_config = {'type': 'arc', 'radius': fillet_radius, 'precision': 0.01, 'interactive': False}
                region = Region.create_polygon(frame, fillet_config=fillet_config)
            ax = axs[idx // 2][idx % 2]
            plot_region(ax, region, label=f'{name} region fillet', color='c')
            ax.set_title(f'Region Polygon Fillet: {name}')
            ax.legend()
            ax.axis('equal')
            self.assertFalse(region.kdb_region.is_empty())
        plt.tight_layout()
        plt.savefig('test_region_polygon_fillet.png')
        plt.close()

    def test_create_rings_fillet(self):
        fig, axs = plt.subplots(2, 2, figsize=(10, 10))
        for idx, (name, verts) in enumerate(self.shapes.items()):
            frame = Frame(verts)
            if name == 'circle':
                region = Region.create_rings(frame, ring_width=3, ring_space=5, ring_num=3)
            else:
                fillet_radius = 1 if name in ('star', 'hexagon') else 2
                fillet_config = {'type': 'arc', 'radius': fillet_radius, 'precision': 0.001, 'interactive': False}
                region = Region.create_rings(frame, ring_width=3, ring_space=5, ring_num=3, fillet_config=fillet_config)
            ax = axs[idx // 2][idx % 2]
            plot_region(ax, region, label=f'{name} rings fillet', color='orange')
            ax.set_title(f'Region Rings Fillet: {name}')
            ax.legend()
            ax.axis('equal')
            self.assertFalse(region.kdb_region.is_empty())
        plt.tight_layout()
        plt.savefig('test_region_rings_fillet.png')
        plt.close()

if __name__ == '__main__':
    unittest.main() 