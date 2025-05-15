import klayout.db as db
import numpy as np
import math
from .frame import Frame
from .utils import logger, um_to_db

class Region:
    """封装 KLayout Region 对象的类，用于创建和操作多边形区域"""
    
    def __init__(self):
        """初始化一个空的 Region 对象"""
        self.kdb_region = db.Region()
        logger.debug("创建空 Region 对象")

    def get_klayout_region(self):
        """获取内部的 KLayout Region 对象
        
        返回:
            db.Region: KLayout Region 对象
        """
        return self.kdb_region

    def __sub__(self, other):
        """布尔减法运算
        
        参数:
            other: 另一个 Region 对象
            
        返回:
            Region: 新的 Region 对象，表示布尔减法的结果
        """
        result = Region()
        result.kdb_region = self.kdb_region - other.get_klayout_region()
        return result

    def __add__(self, other):
        """布尔加法运算（合并）
        
        参数:
            other: 另一个 Region 对象
            
        返回:
            Region: 新的 Region 对象，表示布尔加法的结果
        """
        result = Region()
        result.kdb_region = self.kdb_region + other.get_klayout_region()
        return result

    def __and__(self, other):
        """布尔与运算（交集）
        
        参数:
            other: 另一个 Region 对象
            
        返回:
            Region: 新的 Region 对象，表示布尔与的结果
        """
        result = Region()
        result.kdb_region = self.kdb_region & other.get_klayout_region()
        return result

    def __or__(self, other):
        """布尔或运算（合并，同加法）
        
        参数:
            other: 另一个 Region 对象
            
        返回:
            Region: 新的 Region 对象，表示布尔或的结果
        """
        result = Region()
        result.kdb_region = self.kdb_region | other.get_klayout_region()
        return result

    def __xor__(self, other):
        """布尔异或运算
        
        参数:
            other: 另一个 Region 对象
            
        返回:
            Region: 新的 Region 对象，表示布尔异或的结果
        """
        result = Region()
        result.kdb_region = self.kdb_region ^ other.get_klayout_region()
        return result

    @classmethod
    def create_polygon(cls, frame: Frame, fillet_config: dict = None):
        """从 Frame 对象创建多边形
        
        参数:
            frame: Frame 对象，包含多边形顶点
            fillet_config: 倒角配置字典，例如:
                {"type": "arc", "radius": 0.5, "precision": 0.01, "interactive": True}
                {"type": "adaptive", "convex_radius": 0.5, "concave_radius": 0.2, "precision": 0.01, "interactive": True}
                如果为 None 或空，则不进行倒角。
            
        返回:
            Region: 包含多边形的 Region 对象
        """
        logger.info(f"从 Frame 创建多边形, 原始顶点数: {len(frame.get_vertices())}")
        if fillet_config:
            logger.info(f"应用倒角配置: {fillet_config}")

        processed_frame = frame
        if fillet_config and fillet_config.get("type"):
            fillet_type = fillet_config["type"]
            precision = fillet_config.get("precision", 0.01)
            interactive = fillet_config.get("interactive", True) # 默认为 True，与 Frame 中一致

            # 确保帧是逆时针的，这对于某些倒角逻辑（如凹凸判断）可能很重要
            # Frame的倒角方法内部似乎没有强制，但作为最佳实践，在这里处理
            # 注意: apply_arc_fillet/apply_adaptive_fillet 返回新的Frame实例
            original_vertices_before_ccw_check = processed_frame.get_vertices() # 备份，以防万一
            processed_frame.ensure_counterclockwise() 
            if processed_frame.get_vertices() != original_vertices_before_ccw_check:
                logger.debug("Frame 顶点已转换为逆时针顺序")

            if fillet_type == "arc":
                radius = fillet_config.get("radius", 0)
                if radius > 0:
                    logger.info(f"应用圆弧倒角: 半径={radius}, 精度={precision}")
                    processed_frame = processed_frame.apply_arc_fillet(radius, precision, interactive)
                    logger.info(f"圆弧倒角后顶点数: {len(processed_frame.get_vertices())}")
                    # logger.debug(f"圆弧倒角后顶点: {processed_frame.get_vertices()}")
                else:
                    logger.info("圆弧倒角半径为0，不执行倒角")
            # 暂时用不上，以后引入自定义倒角规则需要
            elif fillet_type == "adaptive":
                convex_radius = fillet_config.get("convex_radius", 0)
                concave_radius = fillet_config.get("concave_radius", 0)
                if convex_radius > 0 or concave_radius > 0:
                    logger.info(f"应用自适应倒角: 凸角半径={convex_radius}, 凹角半径={concave_radius}, 精度={precision}")
                    processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                    logger.info(f"自适应倒角后顶点数: {len(processed_frame.get_vertices())}")
                    # logger.debug(f"自适应倒角后顶点: {processed_frame.get_vertices()}")
                else:
                    logger.info("自适应倒角半径均为0，不执行倒角")
            else:
                logger.warning(f"未知的倒角类型: {fillet_type}，不执行倒角")
        
        # 获取顶点列表 (可能已经过倒角处理)
        vertices = processed_frame.get_vertices()
        
        if not vertices or len(vertices) < 3:
            logger.error(f"顶点数量不足 ({len(vertices)}) 无法创建多边形。原始Frame顶点数: {len(frame.get_vertices())}")
            return cls() # 返回空 Region
        
        # 转换为 KLayout 点列表
        try:
            dpoints = [db.DPoint(um_to_db(x), um_to_db(y)) for x, y in vertices]
            logger.debug(f"dpoints数量: {len(dpoints)}")
            dpolygon = db.DPolygon(dpoints)
            
            result = cls()
            result.kdb_region = db.Region(dpolygon)

            return result
        except Exception as e:
            logger.error(f"创建多边形失败: {e}. 顶点数: {len(vertices)}")
            return cls()

    @classmethod
    def create_rings(cls, initial_frame: Frame, ring_width: float, ring_space: float, ring_num: int, 
                   fillet_config: dict = None):
        """从 Frame 对象创建多个环
        
        参数:
            initial_frame: 初始 Frame 对象
            ring_width: 环宽度
            ring_space: 环间距
            ring_num: 环数量
            fillet_config: 倒角配置字典 (同 create_polygon)。倒角会分别应用于每个环的内外边界。
            
        返回:
            Region: 包含所有环的 Region 对象
        """
        logger.info(f"创建多边形环: 宽度={ring_width}, 间距={ring_space}, 环数={ring_num}")
        if fillet_config:
            logger.info(f"环倒角配置: {fillet_config}")

        result_region = cls() # 用于合并所有环的 Region 对象
        
        # 确保初始 Frame 的顶点是逆时针的, 这对 offset 和后续可能的倒角很重要
        # Frame.offset 应该保持顶点顺序，但以防万一
        initial_frame.ensure_counterclockwise()
        logger.debug(f"初始Frame顶点已确保为逆时针: {initial_frame.get_vertices()}")

        current_inner_boundary_frame = initial_frame

        try:
            for i in range(ring_num):
                logger.debug(f"生成第 {i+1} 环")
                
                # 1. 生成当前环的外边界 Frame
                # offset 正值是外扩，确保 current_inner_boundary_frame 是逆时针，则 offset 结果也应是逆时针
                current_outer_boundary_frame = current_inner_boundary_frame.offset(ring_width)
                current_outer_boundary_frame.ensure_counterclockwise() # 确保外边界也是逆时针

                # 2. 对内外边界 Frame 应用倒角 (如果需要)
                # processed_inner_frame 和 processed_outer_frame 将是倒角后的 Frame
                processed_inner_frame = current_inner_boundary_frame
                processed_outer_frame = current_outer_boundary_frame

                if fillet_config and fillet_config.get("type"):
                    fillet_type = fillet_config["type"]
                    precision = fillet_config.get("precision", 0.01)
                    interactive = fillet_config.get("interactive", True)
                    logger.info(f"为环 {i+1} 应用倒角: 类型={fillet_type}")

                    # 倒角内部Frame (processed_inner_frame)
                    # ensure_counterclockwise 已经在循环开始前对 initial_frame 和 offset 后的 frame 做过
                    if fillet_type == "arc":
                        radius = fillet_config.get("radius", 0)
                        if radius > 0:
                            processed_inner_frame = processed_inner_frame.apply_arc_fillet(radius, precision, interactive)
                            logger.debug(f"环 {i+1} 内边界倒角后顶点: {processed_inner_frame.get_vertices()}")
                    elif fillet_type == "adaptive":
                        convex_radius = fillet_config.get("convex_radius", 0)
                        concave_radius = fillet_config.get("concave_radius", 0)
                        if convex_radius > 0 or concave_radius > 0:
                            processed_inner_frame = processed_inner_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                            logger.debug(f"环 {i+1} 内边界自适应倒角后顶点数量: {len(processed_inner_frame.get_vertices())}")
                    
                    # 倒角外部Frame (processed_outer_frame)
                    if fillet_type == "arc":
                        radius = fillet_config.get("radius", 0)
                        if radius > 0:
                            processed_outer_frame = processed_outer_frame.apply_arc_fillet(radius, precision, interactive)
                            logger.debug(f"环 {i+1} 外边界圆弧倒角后顶点数: {len(processed_outer_frame.get_vertices())}")
                    elif fillet_type == "adaptive":
                        convex_radius = fillet_config.get("convex_radius", 0)
                        concave_radius = fillet_config.get("concave_radius", 0)
                        if convex_radius > 0 or concave_radius > 0:
                            processed_outer_frame = processed_outer_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                            logger.debug(f"环 {i+1} 外边界自适应倒角后顶点数量: {len(processed_outer_frame.get_vertices())}")
                
                # 3. 获取倒角后 (或原始) 的顶点
                inner_vertices = processed_inner_frame.get_vertices()
                outer_vertices = processed_outer_frame.get_vertices()

                if not inner_vertices or len(inner_vertices) < 3 or not outer_vertices or len(outer_vertices) < 3:
                    logger.error(f"环 {i+1}: 内外边界顶点数量不足 (内: {len(inner_vertices)}, 外: {len(outer_vertices)})。跳过此环。")
                    # 为下一个环准备内边界 (基于未倒角的偏移)
                    if ring_space > 0 : # 只有当ring_space > 0 时才进行下一次偏移，否则会原地打转
                         current_inner_boundary_frame = current_outer_boundary_frame.offset(ring_space)
                         current_inner_boundary_frame.ensure_counterclockwise()
                    elif i < ring_num -1: # 如果ring_space是0，且不是最后一个环，则无法继续
                        logger.error("ring_space为0，无法创建多个独立的环。后续环将被跳过。")
                        break
                    continue # 跳过当前环的KLayout区域创建

                # 4. 创建内外环的 DPolygon 和 Region
                inner_dpoints = [db.DPoint(um_to_db(x), um_to_db(y)) for x, y in inner_vertices]
                outer_dpoints = [db.DPoint(um_to_db(x), um_to_db(y)) for x, y in outer_vertices]
                
                inner_dpoly = db.DPolygon(inner_dpoints)
                outer_dpoly = db.DPolygon(outer_dpoints)
                
                kdb_outer_ring_region = db.Region(outer_dpoly)
                kdb_inner_hole_region = db.Region(inner_dpoly)
                
                # 5. 执行布尔运算（外环区域减去内孔区域）
                single_ring_kdb_region = kdb_outer_ring_region - kdb_inner_hole_region
                
                # 6. 合并到结果区域
                result_region.kdb_region += single_ring_kdb_region
                
                # 7. 为下一个环准备内边界 (基于未倒角的、原始偏移定义的外部边界，再进行偏移)
                # 注意：这里我们用 current_outer_boundary_frame (offset后的，未倒角的) 作为下一次迭代的起点
                if ring_space > 0:
                    current_inner_boundary_frame = current_outer_boundary_frame.offset(ring_space)
                    current_inner_boundary_frame.ensure_counterclockwise()
                elif i < ring_num -1: # 如果ring_space是0，且不是最后一个环，则这是一个问题
                    logger.error("ring_space为0，且还有环需要创建，这将导致后续环与当前环重叠或行为未定义。")
                    # 决定是否中断或继续，这里选择中断以避免意外结果
                    break 

            logger.info(f"已完成环的处理和合并，计划创建 {ring_num} 个环")
        except Exception as e:
            logger.error(f"创建环失败: {e}", exc_info=True) # 添加exc_info获取更详细的traceback
            
        return result_region 