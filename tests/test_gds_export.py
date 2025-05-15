import os
import unittest
from gds_utils.frame import Frame
from gds_utils.region import Region
from gds_utils.gds import GDS

import math

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

class TestGDSExport(unittest.TestCase):
    def test_export_shapes_and_rings_to_gds(self):
        # 1. 生成所有多边形和环
        shapes = {
            'square': gen_square(size=10),
            'hexagon': gen_hexagon(r=5),
            'star': gen_star(outer=5, inner=2.5, points=5),
            'circle': gen_circle(r=5, n=256)
        }
        gds = GDS()
        cell = gds.create_cell('TOP')
        base_layer = 10
        # 2. 多边形写入不同layer（除circle外都加倒角）
        for idx, (name, verts) in enumerate(shapes.items()):
            frame = Frame(verts)
            if name == 'circle':
                region = Region.create_polygon(frame)
            else:
                fillet_radius = 1 if name in ('star', 'hexagon') else 2
                fillet_config = {'type': 'arc', 'radius': fillet_radius, 'precision': 0.01, 'interactive': False}
                region = Region.create_polygon(frame, fillet_config=fillet_config)
            layer_info = (base_layer + idx, 0)
            cell.add_region(region, layer_info)
        # 3. 环阵列写入不同layer（除circle外都加倒角）
        for idx, (name, verts) in enumerate(shapes.items()):
            frame = Frame(verts)
            if name == 'circle':
                region = Region.create_rings(frame, ring_width=3, ring_space=5, ring_num=3)
            else:
                fillet_radius = 1 if name in ('star', 'hexagon') else 2
                fillet_config = {'type': 'arc', 'radius': fillet_radius, 'precision': 0.001, 'interactive': False}
                region = Region.create_rings(frame, ring_width=3, ring_space=5, ring_num=3, fillet_config=fillet_config)
            layer_info = (base_layer + 4 + idx, 0)
            cell.add_region(region, layer_info)
        # 4. 导出GDS
        out_gds = 'test_region_export.gds'
        gds.save(out_gds)
        # 5. 检查文件存在且非空
        self.assertTrue(os.path.exists(out_gds))
        self.assertTrue(os.path.getsize(out_gds) > 0)

if __name__ == '__main__':
    unittest.main() 