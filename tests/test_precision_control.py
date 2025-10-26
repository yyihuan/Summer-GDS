"""
阶段二：后端精度控制测试

测试内容：
- 顶点精度转换
- 不同 dbu 的 um_to_db 转换
- Frame 精度应用
- bool 操作在精度转换后的正确性
"""

import pytest
import math
from gds_utils import Frame, Region
from gds_utils.utils import round_vertices, um_to_db, set_global_dbu, get_global_dbu


def approx_equal(a, b, tol=1e-9):
    """检查两个浮点数是否近似相等"""
    return abs(a - b) < tol


def vertices_approx_equal(v1, v2, tol=1e-9):
    """检查两个顶点列表是否近似相等"""
    if len(v1) != len(v2):
        return False
    for (x1, y1), (x2, y2) in zip(v1, v2):
        if not (approx_equal(x1, x2, tol) and approx_equal(y1, y2, tol)):
            return False
    return True


class TestRoundVertices:
    """测试顶点精度转换"""

    def test_round_vertices_basic(self):
        """测试基本的顶点四舍五入"""
        vertices = [(0.0, 0.0), (10.123, 0.0), (10.123, 10.456), (0.0, 10.456)]
        precision = 0.01

        rounded = round_vertices(vertices, precision)

        assert len(rounded) == 4
        assert rounded[0] == (0.0, 0.0)
        assert approx_equal(rounded[1][0], 10.12)
        assert approx_equal(rounded[1][1], 0.0)
        assert approx_equal(rounded[2][0], 10.12)
        assert approx_equal(rounded[2][1], 10.46)
        assert approx_equal(rounded[3][0], 0.0)
        assert approx_equal(rounded[3][1], 10.46)

    def test_round_vertices_with_0_0001_precision(self):
        """测试高精度的顶点转换（0.0001 μm）"""
        vertices = [(0.12346, 0.67891), (1.23456, 2.34567)]
        precision = 0.0001

        rounded = round_vertices(vertices, precision)

        assert approx_equal(rounded[0][0], 0.1235)
        assert approx_equal(rounded[0][1], 0.6789)
        assert approx_equal(rounded[1][0], 1.2346)
        assert approx_equal(rounded[1][1], 2.3457)

    def test_round_vertices_none_precision(self):
        """测试 precision=None 时不转换"""
        vertices = [(0.123, 0.456), (1.234, 2.345)]

        rounded = round_vertices(vertices, None)

        assert rounded == vertices

    def test_round_vertices_empty_list(self):
        """测试空顶点列表"""
        vertices = []
        precision = 0.01

        rounded = round_vertices(vertices, precision)

        assert rounded == []

    def test_round_vertices_negative_coordinates(self):
        """测试负坐标的精度转换"""
        vertices = [(-10.123, -5.456), (-0.001, -0.002)]
        precision = 0.01

        rounded = round_vertices(vertices, precision)

        assert approx_equal(rounded[0][0], -10.12)
        assert approx_equal(rounded[0][1], -5.46)
        assert approx_equal(rounded[1][0], 0.0)
        assert approx_equal(rounded[1][1], 0.0)


class TestUmToDbWithDifferentDbu:
    """测试不同 dbu 下的 um_to_db 转换"""

    def test_um_to_db_default_dbu(self):
        """测试默认 dbu (0.001) 的转换"""
        set_global_dbu(0.001)

        # 1 μm = 1000 db (因为 dbu = 0.001)
        assert um_to_db(1.0) == 1000
        assert um_to_db(0.1) == 100
        assert um_to_db(0.001) == 1

    def test_um_to_db_small_dbu(self):
        """测试小 dbu (0.0001) 的转换"""
        set_global_dbu(0.0001)

        # 1 μm = 10000 db (因为 dbu = 0.0001)
        assert um_to_db(1.0) == 10000
        assert um_to_db(0.1) == 1000
        assert um_to_db(0.0001) == 1

    def test_um_to_db_rounding(self):
        """测试 um_to_db 的四舍五入"""
        set_global_dbu(0.001)

        # 测试四舍五入
        assert um_to_db(1.0001) == 1000  # 1.0001 / 0.001 = 1000.1 → 1000
        # 注：Python round() 使用 "banker's rounding"（舍入到偶数）
        # 1.0005 / 0.001 = 1000.5，round(1000.5) = 1000（舍入到偶数）
        assert um_to_db(1.0004) == 1000  # 1.0004 / 0.001 = 1000.4 → 1000
        assert um_to_db(1.0006) == 1001  # 1.0006 / 0.001 = 1000.6 → 1001

        # 恢复默认值
        set_global_dbu(0.001)


class TestFramePrecisionApplication:
    """测试 Frame 在构造时应用精度"""

    def test_frame_with_precision_application(self):
        """测试 Frame 构造时应用精度转换"""
        vertices = [(0.123, 0.456), (10.789, 0.456), (10.789, 10.123), (0.123, 10.123)]
        precision = 0.01

        frame = Frame(vertices, precision=precision)

        # Frame 的顶点应该被四舍五入
        assert approx_equal(frame.vertices[0][0], 0.12)
        assert approx_equal(frame.vertices[0][1], 0.46)
        assert approx_equal(frame.vertices[1][0], 10.79)
        assert approx_equal(frame.vertices[1][1], 0.46)
        assert approx_equal(frame.vertices[2][0], 10.79)
        assert approx_equal(frame.vertices[2][1], 10.12)
        assert approx_equal(frame.vertices[3][0], 0.12)
        assert approx_equal(frame.vertices[3][1], 10.12)

    def test_frame_without_precision(self):
        """测试 Frame 构造不指定精度"""
        vertices = [(0.123, 0.456), (10.789, 0.456), (10.789, 10.123), (0.123, 10.123)]

        frame = Frame(vertices, precision=None)

        # 顶点应该保持不变
        assert frame.vertices == vertices

    def test_frame_high_precision(self):
        """测试 Frame 使用高精度"""
        vertices = [(0.12346, 0.67891)]
        precision = 0.0001

        frame = Frame(vertices, precision=precision)

        assert approx_equal(frame.vertices[0][0], 0.1235)
        assert approx_equal(frame.vertices[0][1], 0.6789)


class TestBoolOperationWithPrecision:
    """测试 bool 操作在精度转换后的正确性"""

    def test_bool_operation_subtract_with_precision(self):
        """测试减法操作在精度转换后正常工作"""
        set_global_dbu(0.001)
        precision = 0.01

        # 创建两个 polygon
        vertices_outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
        vertices_inner = [(2, 2), (8, 2), (8, 8), (2, 8)]

        frame_outer = Frame(vertices_outer, precision=precision)
        frame_inner = Frame(vertices_inner, precision=precision)

        # 创建 Region
        region_outer = Region.create_polygon(frame_outer)
        region_inner = Region.create_polygon(frame_inner)

        # 执行减法操作
        region_diff = region_outer - region_inner

        # 检查结果不为空
        klayout_region = region_diff.get_klayout_region()
        assert not klayout_region.is_empty()

        # 恢复默认值
        set_global_dbu(0.001)

    def test_bool_operation_add_with_precision(self):
        """测试加法操作在精度转换后正常工作"""
        set_global_dbu(0.001)
        precision = 0.01

        vertices1 = [(0, 0), (5, 0), (5, 5), (0, 5)]
        vertices2 = [(3, 3), (8, 3), (8, 8), (3, 8)]

        frame1 = Frame(vertices1, precision=precision)
        frame2 = Frame(vertices2, precision=precision)

        region1 = Region.create_polygon(frame1)
        region2 = Region.create_polygon(frame2)

        # 执行加法操作（并集）
        region_union = region1 + region2

        klayout_region = region_union.get_klayout_region()
        assert not klayout_region.is_empty()

        set_global_dbu(0.001)

    def test_bool_operation_multiple_regions_same_precision(self):
        """测试多个 Region 使用相同精度的 bool 操作"""
        set_global_dbu(0.001)
        precision = 0.001

        # 创建三个 polygon
        vertices_a = [(0, 0), (10, 0), (10, 10), (0, 10)]
        vertices_b = [(2, 2), (8, 2), (8, 8), (2, 8)]
        vertices_c = [(1, 1), (9, 1), (9, 9), (1, 9)]

        frame_a = Frame(vertices_a, precision=precision)
        frame_b = Frame(vertices_b, precision=precision)
        frame_c = Frame(vertices_c, precision=precision)

        region_a = Region.create_polygon(frame_a)
        region_b = Region.create_polygon(frame_b)
        region_c = Region.create_polygon(frame_c)

        # 执行复杂的 bool 操作：(A - B) & C
        region_diff = region_a - region_b
        region_result = region_diff & region_c

        klayout_region = region_result.get_klayout_region()
        assert not klayout_region.is_empty()

        set_global_dbu(0.001)

    def test_bool_operation_no_precision_regression(self):
        """测试不使用精度时 bool 操作仍然正常（回退测试）"""
        set_global_dbu(0.001)

        vertices_outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
        vertices_inner = [(2, 2), (8, 2), (8, 8), (2, 8)]

        # 不指定 precision
        frame_outer = Frame(vertices_outer, precision=None)
        frame_inner = Frame(vertices_inner, precision=None)

        region_outer = Region.create_polygon(frame_outer)
        region_inner = Region.create_polygon(frame_inner)

        region_diff = region_outer - region_inner

        klayout_region = region_diff.get_klayout_region()
        assert not klayout_region.is_empty()

        set_global_dbu(0.001)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestBoolOperationWithPrecision:
    """测试 bool 操作在精度转换后的正确性"""

    def test_bool_operation_subtract_with_precision(self):
        """测试减法操作在精度转换后正常工作"""
        set_global_dbu(0.001)
        precision = 0.01

        # 创建两个 polygon
        vertices_outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
        vertices_inner = [(2, 2), (8, 2), (8, 8), (2, 8)]

        frame_outer = Frame(vertices_outer, precision=precision)
        frame_inner = Frame(vertices_inner, precision=precision)

        # 创建 Region
        region_outer = Region.create_polygon(frame_outer)
        region_inner = Region.create_polygon(frame_inner)

        # 执行减法操作
        region_diff = region_outer - region_inner

        # 检查结果不为空
        klayout_region = region_diff.get_klayout_region()
        assert not klayout_region.is_empty()

        # 恢复默认值
        set_global_dbu(0.001)

    def test_bool_operation_add_with_precision(self):
        """测试加法操作在精度转换后正常工作"""
        set_global_dbu(0.001)
        precision = 0.01

        vertices1 = [(0, 0), (5, 0), (5, 5), (0, 5)]
        vertices2 = [(3, 3), (8, 3), (8, 8), (3, 8)]

        frame1 = Frame(vertices1, precision=precision)
        frame2 = Frame(vertices2, precision=precision)

        region1 = Region.create_polygon(frame1)
        region2 = Region.create_polygon(frame2)

        # 执行加法操作（并集）
        region_union = region1 + region2

        klayout_region = region_union.get_klayout_region()
        assert not klayout_region.is_empty()

        set_global_dbu(0.001)

    def test_bool_operation_multiple_regions_same_precision(self):
        """测试多个 Region 使用相同精度的 bool 操作"""
        set_global_dbu(0.001)
        precision = 0.001

        # 创建三个 polygon
        vertices_a = [(0, 0), (10, 0), (10, 10), (0, 10)]
        vertices_b = [(2, 2), (8, 2), (8, 8), (2, 8)]
        vertices_c = [(1, 1), (9, 1), (9, 9), (1, 9)]

        frame_a = Frame(vertices_a, precision=precision)
        frame_b = Frame(vertices_b, precision=precision)
        frame_c = Frame(vertices_c, precision=precision)

        region_a = Region.create_polygon(frame_a)
        region_b = Region.create_polygon(frame_b)
        region_c = Region.create_polygon(frame_c)

        # 执行复杂的 bool 操作：(A - B) & C
        region_diff = region_a - region_b
        region_result = region_diff & region_c

        klayout_region = region_result.get_klayout_region()
        assert not klayout_region.is_empty()

        set_global_dbu(0.001)

    def test_bool_operation_no_precision_regression(self):
        """测试不使用精度时 bool 操作仍然正常（回退测试）"""
        set_global_dbu(0.001)

        vertices_outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
        vertices_inner = [(2, 2), (8, 2), (8, 8), (2, 8)]

        # 不指定 precision
        frame_outer = Frame(vertices_outer, precision=None)
        frame_inner = Frame(vertices_inner, precision=None)

        region_outer = Region.create_polygon(frame_outer)
        region_inner = Region.create_polygon(frame_inner)

        region_diff = region_outer - region_inner

        klayout_region = region_diff.get_klayout_region()
        assert not klayout_region.is_empty()

        set_global_dbu(0.001)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
