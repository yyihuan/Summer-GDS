import numpy as np
import math
from .utils import logger

class Frame:
    def __init__(self, vertices):
        self.vertices = vertices

    def is_clockwise(self):
        """检查多边形顶点是否为顺时针方向"""
        n = len(self.vertices)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i][0] * self.vertices[j][1]
            area -= self.vertices[j][0] * self.vertices[i][1]
        return area < 0

    def ensure_counterclockwise(self):
        """确保多边形顶点为逆时针方向"""
        if self.is_clockwise():
            self.vertices = self.vertices[::-1]

    def offset(self, width):
        """生成偏移后的新Frame
        
        参数:
            width: 偏移宽度，正值为外扩，负值为内缩（当前版本仅支持外扩）
            
        返回:
            Frame: 新的Frame对象，表示偏移后的多边形
        """
        n = len(self.vertices)
        offset_edges = []
        
        # 计算每条边的偏移
        for i in range(n):
            p1 = np.array(self.vertices[i])
            p2 = np.array(self.vertices[(i+1)%n])
            
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
            xdiff = np.array([a1[0] - a2[0], b1[0] - b2[0]])
            ydiff = np.array([a1[1] - a2[1], b1[1] - b2[1]])
            
            def det(a, b):
                return a[0] * b[1] - a[1] * b[0]
            
            div = det(xdiff, ydiff)
            if div == 0:
                # 平行，取a2
                new_vertices.append(tuple(a2))
            else:
                d = (det(a1, a2), det(b1, b2))
                x = det(d, xdiff) / div
                y = det(d, ydiff) / div
                new_vertices.append((x, y))

        return Frame(new_vertices)

    def get_vertices(self):
        return self.vertices

    @staticmethod
    def is_convex_vertex(prev_point, curr_point, next_point):
        """判断顶点是否为凸角"""
        edge_1 = np.array(curr_point) - np.array(prev_point)
        edge_2 = np.array(next_point) - np.array(curr_point)
        cross_z = edge_1[0] * edge_2[1] - edge_1[1] * edge_2[0]
        return cross_z > 0

    @staticmethod
    def line_intersection(line1, line2):
        """计算两条线段的交点"""
        p1, p2 = line1
        p3, p4 = line2
        
        xdiff = np.array([p1[0] - p2[0], p3[0] - p4[0]])
        ydiff = np.array([p1[1] - p2[1], p3[1] - p4[1]])
        
        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]
        
        div = det(xdiff, ydiff)
        if div == 0:
            return None  # 平行线返回None
        
        d = (det(p1, p2), det(p3, p4))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div
        return (x, y)
    
    def apply_adaptive_fillet(self, convex_radius, concave_radius, precision=0.01, interactive=True):
        """根据顶点的凹凸性自适应应用不同的倒角半径
        
        Args:
            convex_radius (float or list): 凸角倒角半径，可以是单个浮点数或与顶点数量相同的列表
            concave_radius (float or list): 凹角倒角半径，可以是单个浮点数或与顶点数量相同的列表
            precision (float): 倒角精度
            interactive (bool): 是否启用交互模式
            
        Returns:
            Frame: 倒角后的新Frame对象
        """

        # 两个内外半径都为0，直接返回
        if convex_radius == 0 and concave_radius == 0:
            logger.info("内外半径都为0，不进行倒角")
            return Frame(self.vertices)
        
        logger.info(f"开始自适应倒角: 凸角半径={convex_radius}, 凹角半径={concave_radius}, 精度={precision}, 交互模式={interactive}")
        logger.debug(f"输入顶点列表: {self.vertices}")
        
        n = len(self.vertices)
        if n < 3:
            logger.info("顶点数少于3，不进行倒角")
            return Frame(self.vertices)
            
        # 检查和处理输入参数
        if isinstance(convex_radius, list):
            if len(convex_radius) != n:
                logger.error(f"凸角半径列表长度({len(convex_radius)})与顶点数({n})不匹配")
                return Frame(self.vertices)
            convex_radii = convex_radius
        else:
            convex_radii = [float(convex_radius)] * n
            
        if isinstance(concave_radius, list):
            if len(concave_radius) != n:
                logger.error(f"凹角半径列表长度({len(concave_radius)})与顶点数({n})不匹配")
                return Frame(self.vertices)
            concave_radii = concave_radius
        else:
            concave_radii = [float(concave_radius)] * n
            
        # 如果所有半径都小于等于0，直接返回
        if all(r <= 0 for r in convex_radii) and all(r <= 0 for r in concave_radii):
            logger.info("所有凸凹半径都小于等于0，不进行倒角")
            return Frame(self.vertices)
        
        vertex_radii = []
        for i in range(n):
            prev_idx = (i - 1 + n) % n
            curr_idx = i
            next_idx = (i + 1) % n
            
            prev_point = self.vertices[prev_idx]
            curr_point = self.vertices[curr_idx]
            next_point = self.vertices[next_idx]
            
            is_convex = Frame.is_convex_vertex(prev_point, curr_point, next_point)
            radius = convex_radii[i] if is_convex else concave_radii[i]
            vertex_radii.append(radius)
            logger.debug(f"顶点{i}: 位置={curr_point}, 凹凸性={'凸' if is_convex else '凹'}, 分配半径={radius}")
        
        filleted_vertices = self._apply_arc_fillet_internal(vertex_radii, precision, interactive)
        logger.info(f"自适应倒角完成，输出顶点数: {len(filleted_vertices)}")
        return Frame(filleted_vertices)

    def apply_arc_fillet(self, radius_or_radii_list, precision=0.01, interactive=True):
        """对多边形的顶点应用圆弧倒角。"""
        # 如果倒角列表里都是0，直接返回
        if isinstance(radius_or_radii_list, (int, float)):
            if radius_or_radii_list == 0:
                logger.info("倒角半径为0，不进行倒角")
                return Frame(self.vertices)
            logger.info("使用单一倒角")
        elif isinstance(radius_or_radii_list, (list)):
            if all(r == 0 for r in radius_or_radii_list):
                logger.info("倒角列表里都是0，不进行倒角")
                return Frame(self.vertices)
        else:
            logger.error("ERROR: 倒角参数输入错误")
        
        filleted_vertices = self._apply_arc_fillet_internal(radius_or_radii_list, precision, interactive)
        return Frame(filleted_vertices)

    def _apply_arc_fillet_internal(self, radius_or_radii_list, precision=0.01, interactive=True):
        """对多边形的顶点应用圆弧倒角（内部实现）。"""
        logger.info(f"开始圆弧倒角: 精度={precision}, 交互模式={interactive}")
        
        n = len(self.vertices)
        if n < 3:
            logger.info("顶点数少于3，不进行倒角")
            return self.vertices
        
        logger.debug(f"输入顶点列表: {self.vertices}")
        
        effective_radii = []
        if isinstance(radius_or_radii_list, (int, float)):
            single_radius = float(radius_or_radii_list)
            effective_radii = [single_radius] * n
            logger.debug(f"使用统一半径: {single_radius}")
        elif isinstance(radius_or_radii_list, list):
            if len(radius_or_radii_list) != n:
                logger.warning(f"半径列表长度({len(radius_or_radii_list)})与顶点数({n})不匹配")
                return self.vertices
            effective_radii = [float(r) for r in radius_or_radii_list]
            logger.debug(f"使用半径列表: {effective_radii}")
        else:
            logger.warning(f"无效的半径参数类型: {type(radius_or_radii_list)}")
            return self.vertices
            
        result = []
        all_non_positive = all(r <= 0 for r in effective_radii)
        if all_non_positive:
            logger.info("所有半径都小于等于0，不进行倒角")
            return self.vertices
        
        user_choice = None
        for i in range(n):
            original_radius = effective_radii[i]
            if original_radius <= 0:
                result.append(self.vertices[i])
                continue
                
            prev_idx = (i - 1 + n) % n
            curr_idx = i
            next_idx = (i + 1) % n
            
            prev_point = np.array(self.vertices[prev_idx])
            curr_point = np.array(self.vertices[curr_idx])
            next_point = np.array(self.vertices[next_idx])
            
            vec_curr_prev = prev_point - curr_point
            vec_curr_next = next_point - curr_point
            
            norm_vec_curr_prev = np.linalg.norm(vec_curr_prev)
            norm_vec_curr_next = np.linalg.norm(vec_curr_next)

            if norm_vec_curr_prev < 1e-9 or norm_vec_curr_next < 1e-9:
                result.append(tuple(curr_point))
                continue
                
            unit_vec_curr_prev = vec_curr_prev / norm_vec_curr_prev
            unit_vec_curr_next = vec_curr_next / norm_vec_curr_next
            
            cos_angle = np.dot(unit_vec_curr_prev, unit_vec_curr_next)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle_wedge = np.arccos(cos_angle)

            if angle_wedge < 1e-6 or abs(angle_wedge - math.pi) < 1e-6:
                result.append(tuple(curr_point))
                continue
            
            radius = original_radius
            dist_tangent = radius / math.tan(angle_wedge / 2.0)
            
            half_min_edge = min(norm_vec_curr_prev, norm_vec_curr_next) * 0.5
            max_allowed_dist = min(norm_vec_curr_prev, norm_vec_curr_next) * 0.8
            
            if dist_tangent > max_allowed_dist:
                error_msg = (f"错误: 顶点{i}的切点距离({dist_tangent:.4f})超过边长的0.8倍({max_allowed_dist:.4f}).")
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            elif dist_tangent > half_min_edge and interactive:
                if user_choice is None:
                    print(f"\n警告: 检测到切点距离超过边长的一半，可能导致不理想的倒角效果")
                    print(f"请选择处理方式: 1. 强制按原来指定半径倒角 2. 自动缩小倒角半径")
                    while user_choice not in ['1', '2']:
                        user_choice = input("请输入选项(1或2): ")
                    logger.info(f"用户选择了选项{user_choice}")
                
                if user_choice == '2':
                    radius = half_min_edge * math.tan(angle_wedge / 2.0) * 0.95
                    dist_tangent = half_min_edge * 0.95
                    logger.info(f"顶点{i}: 根据用户选择，调整半径从{original_radius}到{radius}")
                else:
                    logger.info(f"顶点{i}: 根据用户选择，强制使用原半径{radius}")
                    
            p1 = curr_point + unit_vec_curr_prev * dist_tangent
            p2 = curr_point + unit_vec_curr_next * dist_tangent
            
            bisector_vec = unit_vec_curr_prev + unit_vec_curr_next
            if np.linalg.norm(bisector_vec) < 1e-9:
                result.append(tuple(curr_point))
                continue
            bisector_norm_vec = bisector_vec / np.linalg.norm(bisector_vec)
            
            dist_curr_to_center = radius / math.sin(angle_wedge / 2.0)
            fillet_center = curr_point + bisector_norm_vec * dist_curr_to_center
            
            vec_center_p1 = p1 - fillet_center
            angle_of_p1_raw = math.atan2(vec_center_p1[1], vec_center_p1[0])
            
            is_convex_turn = Frame.is_convex_vertex(prev_point, curr_point, next_point)
            
            arc_span_at_center = math.pi - angle_wedge
            if arc_span_at_center < 0: arc_span_at_center += 2*math.pi
            if arc_span_at_center > math.pi: arc_span_at_center = 2*math.pi - arc_span_at_center

            num_segments = max(1, int(math.ceil(radius * arc_span_at_center / precision)))
            sweep_direction = 1.0 if is_convex_turn else -1.0
            
            arc_points = []
            for j in range(num_segments + 1):
                current_sweep_fraction = j / num_segments
                current_interpolated_angle = angle_of_p1_raw + sweep_direction * current_sweep_fraction * arc_span_at_center
                x = fillet_center[0] + radius * math.cos(current_interpolated_angle)
                y = fillet_center[1] + radius * math.sin(current_interpolated_angle)
                arc_points.append((x, y))
            
            result.extend(arc_points)
                
        logger.info(f"圆弧倒角完成，输出顶点数: {len(result)}")
        return result 