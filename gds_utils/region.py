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
    def create_polygon(cls, frame: Frame, fillet_config: dict = None, zoom_config: list = [0, 0]) -> 'Region':
        """从Frame创建多边形Region
        
        参数:
            frame: Frame对象，包含多边形的顶点
            fillet_config: 倒角配置字典
            zoom_config: 缩放配置 [外径缩放, 内径缩放]
            
        返回:
            Region: 包含多边形的 Region 对象
        """
        logger.info(f"从 Frame 创建多边形, 原始顶点数: {len(frame.get_vertices())}")
        if fillet_config:
            logger.info(f"应用倒角配置: {fillet_config}")
        if zoom_config != [0, 0]:
            logger.info(f"应用缩放配置: {zoom_config}")

        processed_frame = frame
        # 首先应用缩放
        if isinstance(zoom_config, list) and len(zoom_config) == 2:
            outer_zoom, inner_zoom = zoom_config
            if outer_zoom != 0:
                logger.info(f"对外径进行缩放: {outer_zoom}")
                processed_frame = processed_frame.offset(outer_zoom)
        else:
            logger.warning(f"缩放配置格式不正确，应为[外径缩放值, 内径缩放值]")

        # 然后应用倒角
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
                    # 检查是否存在半径列表
                    if "radius_list" in fillet_config:
                        radius_list = fillet_config.get("radius_list")
                        logger.info(f"使用半径列表进行倒角: {radius_list}")
                        processed_frame = processed_frame.apply_arc_fillet(radius_list, precision, interactive)
                    else:
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
                   fillet_config: dict = None, zoom_config: list = [0, 0]):
        """从 Frame 对象创建多个环
        
        参数:
            initial_frame: 初始 Frame 对象
            ring_width: 环宽度
            ring_space: 环间距
            ring_num: 环数量
            fillet_config: 倒角配置字典
            zoom_config: 缩放配置 [外径缩放, 内径缩放]
            
        返回:
            Region: 包含所有环的 Region 对象
        """
        logger.info(f"创建多边形环: 宽度={ring_width}, 间距={ring_space}, 环数={ring_num}")
        logger.info(f"环倒角配置: {fillet_config}")
        logger.info(f"环缩放配置: {zoom_config}")

        # 确保初始 Frame 是逆时针的
        initial_frame.ensure_counterclockwise()
        logger.debug(f"初始Frame顶点已确保为逆时针: {initial_frame.get_vertices()}")

        # 1. 生成所有环的边界Frame列表
        outer_frames = []  # 存储所有外边界Frame
        inner_frames = []  # 存储所有内边界Frame
        current_frame = initial_frame

        try:
            for i in range(ring_num):
                # 生成外边界
                outer_frame = current_frame.offset(ring_width)
                outer_frame.ensure_counterclockwise()
                outer_frames.append(outer_frame)
                
                # 生成内边界（当前frame就是内边界）
                inner_frames.append(current_frame)
                
                # 为下一个环准备起始frame
                if ring_space > 0:
                    current_frame = outer_frame.offset(ring_space)
                    current_frame.ensure_counterclockwise()
                elif i < ring_num - 1:
                    logger.error("ring_space为0，无法创建多个独立的环。后续环将被跳过。")
                    break

            # 2. 对每个边界Frame应用缩放和倒角
            processed_outer_frames = []
            processed_inner_frames = []
            
            # 处理外边界
            for frame in outer_frames:
                processed_frame = frame
                
                # 应用缩放
                if isinstance(zoom_config, list) and len(zoom_config) == 2:
                    outer_zoom = zoom_config[0]
                    if outer_zoom != 0:
                        logger.info(f"对外边界进行缩放: {outer_zoom}")
                        processed_frame = processed_frame.offset(outer_zoom)

                
                # 应用倒角
                if fillet_config and fillet_config.get("type"):
                    fillet_type = fillet_config["type"]
                    precision = fillet_config.get("precision", 0.01)
                    interactive = fillet_config.get("interactive", True)
                    
                    if fillet_type == "arc":
                        radius = fillet_config.get("radius", 0)
                        if radius > 0:
                            # 检查是否存在半径列表
                            if "radius_list" in fillet_config:
                                radius_list = fillet_config.get("radius_list")
                                logger.info(f"环外边界使用半径列表进行倒角: {radius_list}")
                                processed_frame = processed_frame.apply_arc_fillet(radius_list, precision, interactive)
                            else:
                                processed_frame = processed_frame.apply_arc_fillet(radius, precision, interactive)
                    elif fillet_type == "adaptive":
                        convex_radius = fillet_config.get("convex_radius", 0)
                        concave_radius = fillet_config.get("concave_radius", 0)
                        if convex_radius > 0 or concave_radius > 0:
                            processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                
                processed_outer_frames.append(processed_frame)
            
            # 处理内边界
            for frame in inner_frames:
                processed_frame = frame
                
                # 应用缩放
                if isinstance(zoom_config, list) and len(zoom_config) == 2:
                    inner_zoom = zoom_config[1]
                    logger.debug(f"inner_zoom: {inner_zoom}")
                    if inner_zoom != 0:
                        logger.info(f"对内边界进行缩放: {inner_zoom}")
                        logger.debug(f"frame before offset: {frame.get_vertices()[:4]}")
                        processed_frame = processed_frame.offset(inner_zoom)
                        logger.debug(f"frame after offset: {processed_frame.get_vertices()[:4]}")
                # 应用倒角
                if fillet_config and fillet_config.get("type"):
                    fillet_type = fillet_config["type"]
                    precision = fillet_config.get("precision", 0.01)
                    interactive = fillet_config.get("interactive", True)
                    
                    if fillet_type == "arc":
                        radius = fillet_config.get("radius", 0)
                        if radius > 0:
                            # 检查是否存在半径列表
                            if "radius_list" in fillet_config:
                                radius_list = fillet_config.get("radius_list")
                                logger.info(f"环内边界使用半径列表进行倒角: {radius_list}")
                                processed_frame = processed_frame.apply_arc_fillet(radius_list, precision, interactive)
                            else:
                                processed_frame = processed_frame.apply_arc_fillet(radius, precision, interactive)
                    elif fillet_type == "adaptive":
                        convex_radius = fillet_config.get("convex_radius", 0)
                        concave_radius = fillet_config.get("concave_radius", 0)
                        if convex_radius > 0 or concave_radius > 0:
                            processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                
                processed_inner_frames.append(processed_frame)

            # 3. 创建最终的Region
            result_region = cls()
            
            # 使用处理后的内外边界创建环
            for i in range(len(processed_outer_frames)):
                if i >= len(processed_inner_frames):
                    break
                    
                outer_frame = processed_outer_frames[i]
                inner_frame = processed_inner_frames[i]
                
                # 获取顶点
                outer_vertices = outer_frame.get_vertices()
                inner_vertices = inner_frame.get_vertices()
                
                if not outer_vertices or len(outer_vertices) < 3 or not inner_vertices or len(inner_vertices) < 3:
                    logger.error(f"环 {i + 1}: 内外边界顶点数量不足 (外: {len(outer_vertices)}, 内: {len(inner_vertices)})。跳过此环。")
                    continue
                
                # 创建DPolygon
                outer_dpoints = [db.DPoint(um_to_db(x), um_to_db(y)) for x, y in outer_vertices]
                inner_dpoints = [db.DPoint(um_to_db(x), um_to_db(y)) for x, y in inner_vertices]
                
                outer_dpoly = db.DPolygon(outer_dpoints)
                inner_dpoly = db.DPolygon(inner_dpoints)
                
                # 创建Region并执行布尔运算
                outer_region = db.Region(outer_dpoly)
                inner_region = db.Region(inner_dpoly)
                ring_region = outer_region - inner_region
                
                # 合并到结果
                result_region.kdb_region += ring_region

            logger.info(f"已完成环的处理和合并，创建了 {len(processed_outer_frames)} 个环")
            
        except Exception as e:
            logger.error(f"创建环失败: {e}", exc_info=True)
            
        return result_region 