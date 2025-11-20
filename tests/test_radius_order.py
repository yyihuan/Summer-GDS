"""测试倒角半径列表的顺序对应关系修复"""
import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gds_utils.frame import Frame
from gds_utils.fillet_utils import sync_reverse_radius_list


class TestRadiusOrderFix(unittest.TestCase):
    """测试半径列表顺序修复功能"""

    def test_sync_reverse_radius_list_format1(self):
        """测试格式1：长度等于顶点数的半径列表反转"""
        fillet_config = {
            "type": "arc",
            "radius_list": [1.0, 2.0, 3.0, 4.0]
        }

        reversed_config = sync_reverse_radius_list(fillet_config, vertex_count=4)

        # 应该反转为 [4.0, 3.0, 2.0, 1.0]
        self.assertEqual(reversed_config["radius_list"], [4.0, 3.0, 2.0, 1.0])
        # 原配置不应被修改
        self.assertEqual(fillet_config["radius_list"], [1.0, 2.0, 3.0, 4.0])

    def test_sync_reverse_radius_list_format2(self):
        """测试格式2：长度等于2倍顶点数的半径列表反转（inner/outer split）"""
        fillet_config = {
            "type": "arc",
            "radius_list": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]  # 前4个inner，后4个outer
        }

        reversed_config = sync_reverse_radius_list(fillet_config, vertex_count=4)

        # 前半部分反转：[4.0, 3.0, 2.0, 1.0]
        # 后半部分反转：[8.0, 7.0, 6.0, 5.0]
        expected = [4.0, 3.0, 2.0, 1.0, 8.0, 7.0, 6.0, 5.0]
        self.assertEqual(reversed_config["radius_list"], expected)

    def test_sync_reverse_radius_list_with_outer_list(self):
        """测试带有 radius_outer_list 的配置"""
        fillet_config = {
            "type": "arc",
            "radius_list": [1.0, 2.0, 3.0, 4.0],
            "radius_outer_list": [5.0, 6.0, 7.0, 8.0]
        }

        reversed_config = sync_reverse_radius_list(fillet_config, vertex_count=4)

        self.assertEqual(reversed_config["radius_list"], [4.0, 3.0, 2.0, 1.0])
        self.assertEqual(reversed_config["radius_outer_list"], [8.0, 7.0, 6.0, 5.0])

    def test_sync_reverse_radius_list_adaptive(self):
        """测试自适应倒角的凸凹半径列表反转"""
        fillet_config = {
            "type": "arc",
            "convex_radius": [1.0, 2.0, 3.0, 4.0],
            "concave_radius": [0.5, 0.6, 0.7, 0.8]
        }

        reversed_config = sync_reverse_radius_list(fillet_config, vertex_count=4)

        self.assertEqual(reversed_config["convex_radius"], [4.0, 3.0, 2.0, 1.0])
        self.assertEqual(reversed_config["concave_radius"], [0.8, 0.7, 0.6, 0.5])

    def test_sync_reverse_radius_list_non_arc(self):
        """测试非arc类型的配置不应被修改"""
        fillet_config = {
            "type": "other",
            "radius_list": [1.0, 2.0, 3.0, 4.0]
        }

        reversed_config = sync_reverse_radius_list(fillet_config, vertex_count=4)

        # 非arc类型应该返回原配置
        self.assertEqual(reversed_config, fillet_config)

    def test_sync_reverse_radius_list_mismatched_length(self):
        """测试长度不匹配的半径列表应保持不变"""
        fillet_config = {
            "type": "arc",
            "radius_list": [1.0, 2.0, 3.0, 4.0, 5.0]  # 5个元素，不是4或8
        }

        reversed_config = sync_reverse_radius_list(fillet_config, vertex_count=4)

        # 长度不匹配，应保持不变
        self.assertEqual(reversed_config["radius_list"], [1.0, 2.0, 3.0, 4.0, 5.0])

    def test_frame_vertex_reversal_detection(self):
        """测试Frame顶点反转检测"""
        # 创建一个顺时针的正方形（会被反转）
        vertices_cw = [
            (0, 0),
            (0, 10),
            (10, 10),
            (10, 0)
        ]

        frame = Frame(vertices_cw)
        first_vertex_before = frame.get_vertices()[0]

        frame.ensure_counterclockwise()
        first_vertex_after = frame.get_vertices()[0]

        # 如果是顺时针，应该被反转，第一个顶点会改变
        self.assertNotEqual(first_vertex_before, first_vertex_after)

    def test_frame_already_counterclockwise(self):
        """测试已经是逆时针的顶点不会被反转"""
        # 创建一个逆时针的正方形
        vertices_ccw = [
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10)
        ]

        frame = Frame(vertices_ccw)
        first_vertex_before = frame.get_vertices()[0]

        frame.ensure_counterclockwise()
        first_vertex_after = frame.get_vertices()[0]

        # 已经是逆时针，不应该被反转
        self.assertEqual(first_vertex_before, first_vertex_after)


if __name__ == '__main__':
    unittest.main()
