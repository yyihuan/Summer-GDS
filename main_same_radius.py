'''
注意，这个代码的不同环对应角使用相同的圆心进行倒角。
而这一feature是基于一个bug实现的。。。不知道会不会在某些图形上出现问题，并且增加了计算量和点数
'''

import klayout.db as db
import numpy as np 
import argparse
import math

def um_to_db(v):
    """单位转换函数（微米转数据库单位）"""
    return int(float(v) * 1000)

def is_clockwise(vertices):
    """检查多边形顶点是否为顺时针方向
    使用Shoelace公式计算有向面积
    返回:
        True: 顺时针
        False: 逆时针
    """
    # 计算有向面积
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    # 如果面积为负，则为顺时针
    return area < 0

def ensure_counterclockwise(vertices):
    """确保多边形顶点为逆时针方向
    如果是顺时针，则反转顶点顺序
    """
    if is_clockwise(vertices):
        return vertices[::-1]  # 反转顶点顺序
    return vertices

# ------------------ 生成多边形环的相关方法 -------------------
def generate_octagon(vert_line, horiz_line, r1, r2, center=(0,0)):
    """生成八边形顶点"""
    a = vert_line / 2
    b = horiz_line / 2
    c_x, c_y = center
    return [
        (c_x - a, c_y + r1), (c_x + a, c_y + r1),
        (c_x + r2, c_y + b), (c_x + r2, c_y - b),
        (c_x + a, c_y - r1), (c_x - a, c_y - r1),
        (c_x - r2, c_y - b), (c_x - r2, c_y + b)
    ]

def cal_parallel_line(p1, p2, width):
    """计算与线段p1p2平行且距离为width的直线方程"""
    x1, y1 = p1
    x2, y2 = p2
    
    if x1 == x2:  # 垂直线
        if x1 > 0:
            return float('inf'), x1+width  # 直接返回x1+width作为t值
        else:
            return float('inf'), x1-width  # 直接返回x1-width作为t值

    elif y1 == y2:  # 水平线
        return 0, y1 + width if y1 > 0 else y1 - width
    else:
        # 计算原始直线斜率和截距
        k = (y2 - y1) / (x2 - x1)
        t = y1 - k * x1
        
        # 计算平行线截距
        d = width * np.sqrt(1 + k*k)
        if t > 0:
            new_t = t + d
        elif t < 0:
            new_t = t - d 
        else:
            # 当t=0时，根据线段方向决定偏移方向
            direction = 1 if (x2 - x1) > 0 else -1
            new_t = direction * d
            
        return k, new_t

def find_intersection(k1, t1, k2, t2):
    """使用numpy计算两条直线的交点"""
    if k1 == float('inf'):  # 第一条是垂直线
        x = t1
        y = k2 * x + t2
    elif k2 == float('inf'):  # 第二条是垂直线
        x = t2
        y = k1 * x + t1
    else:  # 斜线
        A = np.array([[-k1, 1], [-k2, 1]])
        b = np.array([t1, t2])
        x, y = np.linalg.solve(A, b)
    return (x, y)

def generate_ring(vertices, width):
    """生成任意多边形环的外边界顶点（法向量平移法）
    参数:
        vertices: 原始多边形的顶点坐标 [(x1,y1), ..., (xn,yn)]
        width: 环的宽度
    返回:
        新的顶点坐标
    """
    n = len(vertices)
    offset_edges = []
    for i in range(n):
        p1 = np.array(vertices[i])
        p2 = np.array(vertices[(i+1)%n])
        # 边向量
        edge = p2 - p1
        # 单位法向量（逆时针多边形，外侧为右手法则）
        normal = np.array([edge[1], -edge[0]])
        normal = normal / np.linalg.norm(normal)
        # 平移后的边
        q1 = p1 + normal * width
        q2 = p2 + normal * width
        offset_edges.append((q1, q2))
    # 求相邻平移边的交点
    new_vertices = []
    for i in range(n):
        a1, a2 = offset_edges[i-1]
        b1, b2 = offset_edges[i]
        # 求直线交点
        def line_intersection(p1, p2, p3, p4):
            # 直线p1p2与p3p4的交点
            xdiff = np.array([p1[0] - p2[0], p3[0] - p4[0]])
            ydiff = np.array([p1[1] - p2[1], p3[1] - p4[1]])
            def det(a, b):
                return a[0] * b[1] - a[1] * b[0]
            div = det(xdiff, ydiff)
            if div == 0:
                # 平行，取a2
                return tuple(a2)
            d = (det(p1, p2), det(p3, p4))
            x = det(d, xdiff) / div
            y = det(d, ydiff) / div
            return (x, y)
        inter = line_intersection(a1, a2, b1, b2)
        new_vertices.append(inter)
    return new_vertices

def apply_arc_fillet(vertices, radius, precision=0.01):
    """对多边形的顶点应用圆弧倒角
    
    参数:
        vertices: 多边形顶点列表 [(x1,y1), ..., (xn,yn)]
        radius: 倒角半径
        precision: 精度（微米），默认为0.01微米
        
    返回:
        应用倒角后的顶点列表
    """
    if radius <= 0:
        return vertices
        
    n = len(vertices)
    result = []
    
    for i in range(n):
        # 获取当前顶点及其相邻顶点
        prev_idx = (i - 1) % n
        curr_idx = i
        next_idx = (i + 1) % n
        
        prev_point = np.array(vertices[prev_idx])
        curr_point = np.array(vertices[curr_idx])
        next_point = np.array(vertices[next_idx])
        
        # 计算相邻边的方向向量
        vec1 = prev_point - curr_point
        vec2 = next_point - curr_point
        
        # 计算单位方向向量
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
        # 计算角度
        cos_angle = np.dot(vec1_norm, vec2_norm)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        
        # 如果角度太小，跳过倒角
        if angle < 1e-6 or angle > 2 * math.pi - 1e-6:
            result.append(tuple(curr_point))
            continue
            
        # 计算切点到顶点的距离
        tangent_dist = radius / math.tan(angle / 2)
        
        # 限制倒角距离，防止超过边长的一半
        max_dist1 = np.linalg.norm(vec1) / 2
        max_dist2 = np.linalg.norm(vec2) / 2
        if tangent_dist > min(max_dist1, max_dist2):
            # 如果倒角太大，跳过倒角
            result.append(tuple(curr_point))
            continue
        
        # 计算切点
        p1 = curr_point + vec1_norm * tangent_dist
        p2 = curr_point + vec2_norm * tangent_dist
        
        # 计算圆弧中心
        # 使用两个切点和半径计算圆心
        # 圆心在两个切点的垂直平分线上
        mid_point = (p1 + p2) / 2
        # 计算从中点到圆心的向量
        to_center = np.array([-(p2[1] - p1[1]), p2[0] - p1[0]])  # 垂直向量
        to_center = to_center / np.linalg.norm(to_center)  # 单位化
        # 使用毕达哥拉斯定理计算中点到圆心的距离
        mid_to_center_dist = math.sqrt(radius * radius - (np.linalg.norm(p2 - p1) / 2) ** 2)
        # 计算圆心
        center = mid_point + to_center * mid_to_center_dist
        
        # 计算圆弧的起始角度和结束角度
        start_angle = math.atan2(p1[1] - center[1], p1[0] - center[0])
        end_angle = math.atan2(p2[1] - center[1], p2[0] - center[0])
        
        # 确保角度是逆时针方向
        if end_angle < start_angle:
            end_angle += 2 * math.pi
            
        # 计算需要的圆弧段数
        arc_length = radius * abs(end_angle - start_angle)
        num_segments = max(1, int(math.ceil(arc_length / precision)))
        
        # 生成圆弧点
        for j in range(num_segments + 1):
            t = j / num_segments
            angle = start_angle + t * (end_angle - start_angle)
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            result.append((x, y))
            
    return result

def create_polygon_rings(vertices, width, space, ring_num, fillet_radius=0, precision=0.01):
    """从给定顶点创建多个环
    参数:
        vertices: 初始多边形顶点
        width: 环宽度
        space: 环间距
        ring_num: 环数量
        fillet_radius: 倒角半径（默认为0，不倒角）
        precision: 倒角精度（微米），默认为0.01微米
    返回:
        inner_vertices_list, outer_vertices_list: 内外环顶点列表
    """
    inner_vertices_list = []
    outer_vertices_list = []
    
    # 如果需要倒角，先对初始多边形应用倒角
    if fillet_radius > 0:
        vertices = apply_arc_fillet(vertices, fillet_radius, precision)
    
    current_vertices = vertices
    
    for _ in range(ring_num):
        inner_vertices_list.append(current_vertices)
        outer_vertices = generate_ring(current_vertices, width)
        
        # 如果需要倒角，对外环也应用倒角
        if fillet_radius > 0:
            outer_vertices = apply_arc_fillet(outer_vertices, fillet_radius, precision)
            
        outer_vertices_list.append(outer_vertices)
        current_vertices = generate_ring(outer_vertices, space)
        
        # 如果需要倒角，对下一个内环也应用倒角
        if fillet_radius > 0 and _ < ring_num - 1:
            current_vertices = apply_arc_fillet(current_vertices, fillet_radius, precision)
        
    return inner_vertices_list, outer_vertices_list

def create_gds(inner_vertices_list, outer_vertices_list, output_file="polygon_rings.gds"):
    """创建并保存GDS文件
    参数:
        inner_vertices_list: 内环顶点列表
        outer_vertices_list: 外环顶点列表
        output_file: 输出文件名
    """
    # 创建布局并设置数据库单位（1单位=1纳米）
    layout = db.Layout()
    layout.dbu = 0.001  # 设置单位为微米

    # 定义图层（层号1/0）
    layer_info = db.LayerInfo(1, 0)
    layer_index = layout.layer(layer_info)

    # 创建顶层单元格
    cell = layout.create_cell("TOP")

    # 合并所有环的区域
    region_merged = db.Region()

    for inner, outer in zip(inner_vertices_list, outer_vertices_list):
        # 转换为KLayout多边形
        inner_points = [db.Point(um_to_db(x), um_to_db(y)) for x, y in inner]
        outer_points = [db.Point(um_to_db(x), um_to_db(y)) for x, y in outer]
        
        inner_poly = db.DPolygon(inner_points)
        outer_poly = db.DPolygon(outer_points)
        
        # 执行布尔运算
        region_outer = db.Region(outer_poly)
        region_inner = db.Region(inner_poly)
        final_region = region_outer - region_inner
        
        # 合并到总区域
        region_merged += final_region

    # 写入图层
    cell.shapes(layer_index).insert(region_merged)

    # 保存GDS文件
    layout.write(output_file)
    print(f"已保存GDS文件: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='生成多边形环GDS文件')
    parser.add_argument('--vertices', type=str, required=True, help='多边形顶点，格式为x1,y1:x2,y2:...')
    parser.add_argument('--width', type=float, default=10, help='环宽度')
    parser.add_argument('--space', type=float, default=12, help='环间距')
    parser.add_argument('--ring_num', type=int, default=3, help='环数量')
    parser.add_argument('--output', default='polygon_rings.gds', help='输出文件名')
    parser.add_argument('--force_ccw', action='store_true', help='强制逆时针方向')
    parser.add_argument('--fillet_radius', type=float, default=0, help='倒角半径（默认为0，不倒角）')
    parser.add_argument('--precision', type=float, default=0.01, help='倒角精度（微米），默认为0.01微米')
    
    args = parser.parse_args()
    
    # 解析顶点字符串 "x1,y1:x2,y2:..."
    try:
        vertex_pairs = args.vertices.split(':')
        vertices = []
        for pair in vertex_pairs:
            x, y = map(float, pair.split(','))
            vertices.append((x, y))
    except Exception as e:
        print(f"错误: 顶点格式不正确，应为 'x1,y1:x2,y2:...'")
        print(f"详细错误: {e}")
        return
    
    # 检查并修正顶点顺序
    if args.force_ccw:
        original_direction = "顺时针" if is_clockwise(vertices) else "逆时针"
        vertices = ensure_counterclockwise(vertices)
        print(f"顶点顺序: 原始为{original_direction}，已调整为逆时针")
    
    # 生成环
    inner_vertices_list, outer_vertices_list = create_polygon_rings(
        vertices, args.width, args.space, args.ring_num, args.fillet_radius, args.precision
    )
    
    # 创建并保存GDS文件
    create_gds(inner_vertices_list, outer_vertices_list, args.output)

if __name__ == "__main__":
    main()