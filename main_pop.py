import klayout.db as db
import numpy as np
import argparse
import math
import logging
import os

# 初始化全局logger
logger = None

# 设置日志
def setup_logging(show_log=True):
    """配置日志系统
    
    参数:
        show_log: 是否在控制台显示日志
    """
    global logger
    handlers = [logging.FileHandler("fillet_debug.log", mode='w')]  # 总是写入文件
    if show_log:
        handlers.append(logging.StreamHandler())  # 根据参数决定是否输出到控制台
        
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    logger = logging.getLogger("polygon_fillet")
    return logger

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

def is_convex_vertex(prev_point, curr_point, next_point):
    """判断顶点是否为凸角
    
    参数:
        prev_point: 前一个顶点坐标
        curr_point: 当前顶点坐标
        next_point: 后一个顶点坐标
        
    返回:
        True: 凸角
        False: 凹角
    """
    # 计算边向量
    edge_1 = np.array(curr_point) - np.array(prev_point)
    edge_2 = np.array(next_point) - np.array(curr_point)
    
    # 计算叉积的z分量
    cross_z = edge_1[0] * edge_2[1] - edge_1[1] * edge_2[0]
    
    result = cross_z > 0
    logger.debug(f"判断顶点凹凸性: 点={curr_point}, 前点={prev_point}, 后点={next_point}, 叉积={cross_z}, 凸角={result}")
    
    # 对于逆时针多边形，叉积为正表示凸角（左转），为负表示凹角（右转）
    return result

def apply_adaptive_fillet(vertices, convex_radius, concave_radius, precision=0.01, interactive=True):
    """根据顶点的凹凸性自适应应用不同的倒角半径
    
    参数:
        vertices: 多边形顶点列表
        convex_radius: 凸角的倒角半径
        concave_radius: 凹角的倒角半径
        precision: 精度
        interactive: 是否启用交互式用户选择
        
    返回:
        应用倒角后的顶点列表
    """
    logger.info(f"开始自适应倒角: 凸角半径={convex_radius}, 凹角半径={concave_radius}, 精度={precision}, 交互模式={interactive}")
    logger.debug(f"输入顶点列表: {vertices}")
    
    if convex_radius <= 0 and concave_radius <= 0:
        logger.info("凸凹半径都小于等于0，不进行倒角")
        return vertices
        
    n = len(vertices)
    if n < 3:
        logger.info("顶点数少于3，不进行倒角")
        return vertices
    
    # 为每个顶点准备对应的半径
    vertex_radii = []
    for i in range(n):
        prev_idx = (i - 1 + n) % n
        curr_idx = i
        next_idx = (i + 1) % n
        
        prev_point = vertices[prev_idx]
        curr_point = vertices[curr_idx]
        next_point = vertices[next_idx]
        
        is_convex = is_convex_vertex(prev_point, curr_point, next_point)
        radius = convex_radius if is_convex else concave_radius
        vertex_radii.append(radius)
        logger.debug(f"顶点{i}: 位置={curr_point}, 凹凸性={'凸' if is_convex else '凹'}, 分配半径={radius}")
    
    # 调用新的 apply_arc_fillet 函数处理每个顶点
    result = apply_arc_fillet(vertices, vertex_radii, precision, interactive)
    logger.info(f"自适应倒角完成，输出顶点数: {len(result)}")
    return result

def apply_arc_fillet(vertices, radius_or_radii_list, precision=0.01, interactive=True):
    """对多边形的顶点应用圆弧倒角。
    可以接受单个半径值（应用于所有顶点）或一个半径列表（每个顶点对应一个半径）。
    
    参数:
        vertices: 多边形顶点列表 [(x1,y1), ..., (xn,yn)]
        radius_or_radii_list: 单个倒角半径值或每个顶点对应的倒角半径列表
        precision: 精度（微米），默认为0.01微米
        interactive: 是否启用交互式用户选择，当切点距离介于边长的0.5-0.8倍时
        
    返回:
        应用倒角后的顶点列表
        
    异常:
        ValueError: 当切点距离超过边长0.8倍时抛出
    """
    logger.info(f"开始圆弧倒角: 精度={precision}, 交互模式={interactive}")
    
    n = len(vertices)
    if n < 3:
        logger.info("顶点数少于3，不进行倒角")
        return vertices
    
    logger.debug(f"输入顶点列表: {vertices}")
    
    effective_radii = []
    if isinstance(radius_or_radii_list, (int, float)):
        # 单个半径值
        single_radius = float(radius_or_radii_list)
        effective_radii = [single_radius] * n
        logger.debug(f"使用统一半径: {single_radius}")
    elif isinstance(radius_or_radii_list, list):
        # 半径列表
        if len(radius_or_radii_list) != n:
            # 半径列表长度与顶点数不匹配
            logger.warning(f"半径列表长度({len(radius_or_radii_list)})与顶点数({n})不匹配")
            return vertices 
        effective_radii = [float(r) for r in radius_or_radii_list]
        logger.debug(f"使用半径列表: {effective_radii}")
    else:
        #提供了无效的半径参数类型
        logger.warning(f"无效的半径参数类型: {type(radius_or_radii_list)}")
        return vertices 
        
    result = []
    # 检查是否所有半径都小于等于0，若是，则提前返回原始顶点列表
    # 这是一个优化，因为循环内部也会逐个处理半径<=0的情况
    all_non_positive = True
    for r_val in effective_radii:
        if r_val > 0:
            all_non_positive = False
            break
    if all_non_positive:
        logger.info("所有半径都小于等于0，不进行倒角")
        return vertices
    
    # 用户交互选择标志，只在第一次遇到需要选择的情况时提示
    user_choice = None
    
    for i in range(n):
        original_radius = effective_radii[i]
        if original_radius <= 0:
            logger.debug(f"顶点{i}: 半径={original_radius}，小于等于0，跳过倒角")
            result.append(vertices[i])
            continue
            
        prev_idx = (i - 1 + n) % n
        curr_idx = i
        next_idx = (i + 1) % n
        
        prev_point = np.array(vertices[prev_idx])
        curr_point = np.array(vertices[curr_idx])
        next_point = np.array(vertices[next_idx])
        
        logger.debug(f"处理顶点{i}: 位置={curr_point}, 前点={prev_point}, 后点={next_point}, 半径={original_radius}")
        
        vec_curr_prev = prev_point - curr_point
        vec_curr_next = next_point - curr_point
        
        norm_vec_curr_prev = np.linalg.norm(vec_curr_prev)
        norm_vec_curr_next = np.linalg.norm(vec_curr_next)

        if norm_vec_curr_prev < 1e-9 or norm_vec_curr_next < 1e-9:
            logger.warning(f"顶点{i}: 相邻边长度过小，跳过倒角")
            result.append(tuple(curr_point))
            continue
            
        unit_vec_curr_prev = vec_curr_prev / norm_vec_curr_prev
        unit_vec_curr_next = vec_curr_next / norm_vec_curr_next
        
        cos_angle = np.dot(unit_vec_curr_prev, unit_vec_curr_next)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_wedge = np.arccos(cos_angle)
        logger.debug(f"顶点{i}: 角度={angle_wedge * 180 / math.pi}度")

        if angle_wedge < 1e-6 or abs(angle_wedge - math.pi) < 1e-6:
            logger.warning(f"顶点{i}: 角度接近0或180度，跳过倒角")
            result.append(tuple(curr_point))
            continue
        
        # 使用临时变量保存最终使用的半径
        radius = original_radius
        
        # 计算切点距离
        dist_tangent = radius / math.tan(angle_wedge / 2.0)
        
        # 计算几何限制值: 0.5倍边长和0.8倍边长
        half_min_edge = min(norm_vec_curr_prev, norm_vec_curr_next) * 0.5
        max_allowed_dist = min(norm_vec_curr_prev, norm_vec_curr_next) * 0.8  # 新的0.8倍限制
        
        # 处理切点距离超限情况
        if dist_tangent > max_allowed_dist:
            error_msg = (f"错误: 顶点{i}的切点距离({dist_tangent:.4f})超过边长的0.8倍({max_allowed_dist:.4f})。\n"
                        f"当前顶点: {tuple(curr_point)}\n"
                        f"当前倒角半径: {radius}\n"
                        f"相邻边长: {norm_vec_curr_prev:.4f}, {norm_vec_curr_next:.4f}")
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        elif dist_tangent > half_min_edge and interactive:
            # 当切点距离在0.5-0.8倍边长之间时，需要用户交互选择
            if user_choice is None:
                print(f"\n警告: 检测到切点距离超过边长的一半，可能导致不理想的倒角效果")
                print(f"当前切点距离: {dist_tangent:.4f}, 边长的一半: {half_min_edge:.4f}")
                print(f"请选择处理方式:")
                print(f"1. 强制按原来指定半径倒角")
                print(f"2. 自动缩小倒角半径以适应几何约束")
                
                while user_choice not in ['1', '2']:
                    user_choice = input("请输入选项(1或2): ")
                
                logger.info(f"用户选择了选项{user_choice}")
            
            if user_choice == '2':
                # 自动缩小半径选项
                radius = half_min_edge * math.tan(angle_wedge / 2.0) * 0.95  # 使用95%的最大允许值
                dist_tangent = half_min_edge * 0.95  # 更新切点距离
                logger.info(f"顶点{i}: 根据用户选择，调整半径从{original_radius}到{radius}")
            else:
                # 强制使用原半径选项，无需修改radius和dist_tangent
                logger.info(f"顶点{i}: 根据用户选择，强制使用原半径{radius}")
                
        logger.debug(f"顶点{i}: 切点距离={dist_tangent}, 相邻边长={norm_vec_curr_prev},{norm_vec_curr_next}")
        
        p1 = curr_point + unit_vec_curr_prev * dist_tangent
        p2 = curr_point + unit_vec_curr_next * dist_tangent
        
        bisector_vec = unit_vec_curr_prev + unit_vec_curr_next
        if np.linalg.norm(bisector_vec) < 1e-9:
            logger.warning(f"顶点{i}: 角平分线向量过小，跳过倒角")
            result.append(tuple(curr_point))
            continue
        bisector_norm_vec = bisector_vec / np.linalg.norm(bisector_vec)
        
        dist_curr_to_center = radius / math.sin(angle_wedge / 2.0)
        fillet_center = curr_point + bisector_norm_vec * dist_curr_to_center
        logger.debug(f"顶点{i}: 圆心={fillet_center}, 圆心到顶点距离={dist_curr_to_center}")
        
        vec_center_p1 = p1 - fillet_center
        angle_of_p1_raw = math.atan2(vec_center_p1[1], vec_center_p1[0])
        
        is_convex_turn = is_convex_vertex(prev_point, curr_point, next_point)
        logger.debug(f"顶点{i}: 凹凸性={'凸' if is_convex_turn else '凹'}")
        
        arc_span_at_center = math.pi - angle_wedge
        if arc_span_at_center < 0: arc_span_at_center += 2*math.pi
        if arc_span_at_center > math.pi: arc_span_at_center = 2*math.pi - arc_span_at_center

        num_segments = max(1, int(math.ceil(radius * arc_span_at_center / precision)))
        sweep_direction = 1.0 if is_convex_turn else -1.0
        logger.debug(f"顶点{i}: 圆弧角度={arc_span_at_center * 180 / math.pi}度, 段数={num_segments}, 扫描方向={sweep_direction}")
        
        arc_points = []
        for j in range(num_segments + 1):
            current_sweep_fraction = j / num_segments
            current_interpolated_angle = angle_of_p1_raw + sweep_direction * current_sweep_fraction * arc_span_at_center
            x = fillet_center[0] + radius * math.cos(current_interpolated_angle)
            y = fillet_center[1] + radius * math.sin(current_interpolated_angle)
            arc_points.append((x, y))
        
        logger.debug(f"顶点{i}: 生成{len(arc_points)}个圆弧点")
        result.extend(arc_points)
            
    logger.info(f"圆弧倒角完成，输出顶点数: {len(result)}")
    return result

def create_polygon_rings(vertices, width, space, ring_num, fillet_radius=0, precision=0.01, interactive=True):
    """从给定顶点创建多个环
    参数:
        vertices: 初始多边形顶点
        width: 环宽度
        space: 环间距
        ring_num: 环数量
        fillet_radius: 倒角半径（默认为0，不倒角）
        precision: 倒角精度（微米），默认为0.01微米
        interactive: 是否启用交互式用户选择
    返回:
        inner_vertices_list, outer_vertices_list: 内外环顶点列表
    """
    # 记录多边形的方向
    direction = "顺时针" if is_clockwise(vertices) else "逆时针"
    logger.info(f"创建多边形环: 宽度={width}, 间距={space}, 环数={ring_num}, 倒角半径={fillet_radius}, 精度={precision}, 交互模式={interactive}")
    
    # 首先生成所有未倒角的多边形环
    raw_inner_vertices_list = []
    raw_outer_vertices_list = []
    
    current_vertices = vertices
    
    for i in range(ring_num):
        logger.debug(f"生成第{i+1}环")
        raw_inner_vertices_list.append(current_vertices)
        outer_vertices = generate_ring(current_vertices, width)
        raw_outer_vertices_list.append(outer_vertices)
        current_vertices = generate_ring(outer_vertices, space)
        
    # 如果不需要倒角，直接返回
    if fillet_radius <= 0:
        logger.info("倒角半径小于等于0，不进行倒角")
        return raw_inner_vertices_list, raw_outer_vertices_list
    
    # 应用倒角
    inner_vertices_list = []
    outer_vertices_list = []
    
    # 对每对内外环应用适配倒角
    for i, (inner_vertices, outer_vertices) in enumerate(zip(raw_inner_vertices_list, raw_outer_vertices_list)):
        logger.info(f"对第{i+1}环应用倒角")
        
        # 内环：凸角用fillet_radius，凹角用fillet_radius+width
        logger.debug(f"处理第{i+1}环内环, 凸角半径={fillet_radius}, 凹角半径={fillet_radius+width}")
        inner_filleted = apply_adaptive_fillet(inner_vertices, fillet_radius, fillet_radius+width, precision, interactive)
        inner_vertices_list.append(inner_filleted)
        
        # 外环：凸角用fillet_radius+width，凹角用fillet_radius
        logger.debug(f"处理第{i+1}环外环, 凸角半径={fillet_radius+width}, 凹角半径={fillet_radius}")
        outer_filleted = apply_adaptive_fillet(outer_vertices, fillet_radius+width, fillet_radius, precision, interactive)
        outer_vertices_list.append(outer_filleted)
    
    return inner_vertices_list, outer_vertices_list

def init_gds_layout(input_file=None, dbu=0.001):
    """初始化或读取GDS布局
    
    参数:
        input_file: GDS输入文件路径，如果为None则创建新的布局
        dbu: 数据库单位（默认0.001，即1纳米）
        
    返回:
        layout: 布局对象
    """
    layout = db.Layout()
    if input_file:
        try:
            layout.read(input_file)
            logger.info(f"已读取GDS文件: {input_file}")
        except Exception as e:
            logger.error(f"读取GDS文件失败: {e}")
            raise
    else:
        layout.dbu = dbu  # 设置单位为微米
        logger.info("已创建新的GDS布局")
    return layout

def get_or_create_cell(layout, cell_name="TOP"):
    """获取或创建单元格
    
    参数:
        layout: 布局对象
        cell_name: 单元格名称
        
    返回:
        cell: 单元格对象
    """
    cell = layout.cell(cell_name)
    if cell is None:
        cell = layout.create_cell(cell_name)
        logger.info(f"已创建新的单元格: {cell_name}")
    else:
        logger.info(f"已获取现有单元格: {cell_name}")
    return cell

def get_or_create_layer(layout, layer_info=(1, 0)):
    """获取或创建图层
    
    参数:
        layout: 布局对象
        layer_info: 图层信息元组 (layer_num, datatype)
        
    返回:
        layer_index: 图层索引
    """
    layer_num, datatype = layer_info
    layer_info_obj = db.LayerInfo(layer_num, datatype)
    layer_index = layout.layer(layer_info_obj)
    logger.info(f"已获取图层: {layer_num}/{datatype}")
    return layer_index

def create_polygon(vertices, fillet_radius=0, precision=0.01, interactive=True):
    """创建一个带倒角的多边形
    
    参数:
        vertices: 多边形顶点列表 [(x1,y1), ..., (xn,yn)]
        fillet_radius: 倒角半径（默认为0，不倒角）
        precision: 倒角精度（微米），默认为0.01微米
        interactive: 是否启用交互式用户选择
        
    返回:
        region: 多边形区域对象
    """
    logger.info(f"创建多边形: 倒角半径={fillet_radius}, 精度={precision}, 交互模式={interactive}")
    
    # 如果需要倒角，应用倒角处理
    if fillet_radius > 0:
        vertices = apply_arc_fillet(vertices, fillet_radius, precision, interactive)
        
    # 转换为KLayout多边形
    points = [db.Point(um_to_db(x), um_to_db(y)) for x, y in vertices]
    polygon = db.DPolygon(points)
    
    # 创建区域
    region = db.Region(polygon)
    logger.info("多边形创建完成")
    
    return region

def create_rings(inner_vertices_list, outer_vertices_list):
    """处理多边形环并创建区域
    
    参数:
        inner_vertices_list: 内环顶点列表
        outer_vertices_list: 外环顶点列表
        
    返回:
        region_merged: 合并后的区域
    """
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
    
    logger.info("已完成环的处理和合并")
    return region_merged

def open_gds(input_file=None, cell_name="TOP", layer_info=(1, 0)):
    """初始化或打开GDS文件，并返回相关对象
    
    参数:
        input_file: 输入文件名（如果要打开现有文件）
        cell_name: 单元格名称
        layer_info: 图层信息元组 (layer_num, datatype)
        
    返回:
        tuple: (layout, cell, layer_index) 布局对象、单元格对象和图层索引
    """
    # 初始化或读取布局
    layout = init_gds_layout(input_file)
    
    # 获取或创建单元格
    cell = get_or_create_cell(layout, cell_name)
    
    # 获取或创建图层
    layer_index = get_or_create_layer(layout, layer_info)
    
    return layout, cell, layer_index

def save_gds(layout, output_file):
    """保存GDS文件
    
    参数:
        layout: 布局对象
        output_file: 输出文件路径
    """
    try:
        layout.write(output_file)
        logger.info(f"已保存GDS文件: {output_file}")
        print(f"已保存GDS文件: {output_file}")
    except Exception as e:
        logger.error(f"保存GDS文件失败: {e}")
        raise

def create_gds(inner_vertices_list, outer_vertices_list, output_file="polygon_rings.gds", input_file=None, 
               cell_name="TOP", layer_info=(1, 0)):
    """创建并保存GDS文件
    
    参数:
        inner_vertices_list: 内环顶点列表
        outer_vertices_list: 外环顶点列表
        output_file: 输出文件名
        input_file: 输入文件名（如果要在现有文件基础上修改）
        cell_name: 单元格名称
        layer_info: 图层信息元组 (layer_num, datatype)
    """
    # 初始化或读取布局
    layout = init_gds_layout(input_file)
    
    # 获取或创建单元格
    cell = get_or_create_cell(layout, cell_name)
    
    # 获取或创建图层
    layer_index = get_or_create_layer(layout, layer_info)
    
    # 处理环
    region_merged = create_rings(inner_vertices_list, outer_vertices_list)
    
    # 写入图层
    cell.shapes(layer_index).insert(region_merged)
    
    # 保存GDS文件
    save_gds(layout, output_file)

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
    parser.add_argument('--interactive', action='store_true', default=True, help='启用交互式选择模式（默认启用）')
    parser.add_argument('--no-interactive', dest='interactive', action='store_false', help='禁用交互式选择模式')
    parser.add_argument('--quiet', action='store_true', help='不在控制台显示日志信息（但仍然保存到文件）')
    parser.add_argument('--input', default=None, help='输入GDS文件（可选）')
    parser.add_argument('--cell', default="TOP", help='单元格名称')
    parser.add_argument('--layer', type=str, default="1,0", help='图层信息，格式为layer_num,datatype')
    
    args = parser.parse_args()
    
    # 设置日志
    global logger
    logger = setup_logging(not args.quiet)
    
    # 记录参数信息
    logger.info(f"命令行参数: {args}")
    
    # 解析图层信息
    layer_num, datatype = map(int, args.layer.split(','))
    layer_info = (layer_num, datatype)
    
    # 解析顶点字符串 "x1,y1:x2,y2:..."
    try:
        vertex_pairs = args.vertices.split(':')
        vertices = []
        for pair in vertex_pairs:
            x, y = map(float, pair.split(','))
            vertices.append((x, y))
        logger.debug(f"解析得到的顶点列表: {vertices}")
    except Exception as e:
        error_msg = f"错误: 顶点格式不正确，应为 'x1,y1:x2,y2:...'"
        logger.error(f"{error_msg}, 详细错误: {e}")
        print(f"{error_msg}")
        print(f"详细错误: {e}")
        return
    
    # 检查并修正顶点顺序
    if args.force_ccw:
        original_direction = "顺时针" if is_clockwise(vertices) else "逆时针"
        vertices = ensure_counterclockwise(vertices)
        logger.info(f"顶点顺序: 原始为{original_direction}，已调整为逆时针")
        if not args.quiet:  # 只在非安静模式下打印
            print(f"顶点顺序: 原始为{original_direction}，已调整为逆时针")
    
    # 生成环
    inner_vertices_list, outer_vertices_list = create_polygon_rings(
        vertices, args.width, args.space, args.ring_num, args.fillet_radius, args.precision, args.interactive
    )
    
    # 打开或创建GDS文件
    layout, cell, layer_index = open_gds(args.input, args.cell, layer_info)
    
    # 创建环区域
    region_merged = create_rings(inner_vertices_list, outer_vertices_list)
    
    # 写入图层
    cell.shapes(layer_index).insert(region_merged)
    
    # 保存GDS文件
    save_gds(layout, args.output)

if __name__ == "__main__":
    main()