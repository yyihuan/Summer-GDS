import klayout.db as db
import numpy as np
import math
from .frame import Frame
from .utils import logger, um_to_db
from typing import Union, List

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
    def create_polygon(cls, frame: Frame, fillet_config: dict = None, zoom_config: Union[int, float] = 0) -> 'Region':
        """从Frame创建多边形Region
        
        参数:
            frame: Frame对象，包含多边形的顶点
            fillet_config: 倒角配置字典
            zoom_config: 缩放值（正值表示向外扩展，负值表示向内收缩）
            
        返回:
            Region: 包含多边形的 Region 对象
        """
        logger.info(f"从 Frame 创建多边形, 原始顶点数: {len(frame.get_vertices())}")
        if fillet_config:
            logger.info(f"应用倒角配置: {fillet_config}")

        processed_frame = frame
        # 首先应用缩放
        if isinstance(zoom_config, (int, float)):
            if zoom_config != 0:
                logger.info(f"进行缩放: {zoom_config}")
                processed_frame = processed_frame.offset(zoom_config)
        else:
            logger.warning(f"缩放配置格式不正确，应为数值")

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
                    # 检查是否存在半径列表
                    if "radius_list" in fillet_config:
                        radius_list = fillet_config.get("radius_list")
                        # 根据zoom_config调整半径列表
                        if isinstance(zoom_config, (int, float)) and zoom_config != 0:
                            # 对于向外扩展(zoom_config > 0)，凸角半径增加，凹角半径减少
                            # 对于向内收缩(zoom_config < 0)，凸角半径减少，凹角半径增加
                            convex_radius = [r + zoom_config for r in radius_list]
                            concave_radius = [r - zoom_config for r in radius_list]
                            logger.info(f"使用调整后的半径列表进行倒角: 凸角={convex_radius}, 凹角={concave_radius}")
                            processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                        else:
                            logger.info(f"使用原始半径列表进行倒角: {radius_list}")
                            processed_frame = processed_frame.apply_arc_fillet(radius_list, precision, interactive)
                    else:
                        # 根据zoom_config调整单一半径
                        if isinstance(zoom_config, (int, float)) and zoom_config != 0:
                            # 对于向外扩展(zoom_config > 0)，凸角半径增加，凹角半径减少
                            # 对于向内收缩(zoom_config < 0)，凸角半径减少，凹角半径增加
                            convex_radius = radius + zoom_config
                            concave_radius = radius - zoom_config
                            logger.info(f"应用调整后的倒角: 凸角半径={convex_radius}, 凹角半径={concave_radius}")
                            processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                        else:
                            logger.info(f"应用圆弧倒角: 半径={radius}, 精度={precision}")
                            processed_frame = processed_frame.apply_arc_fillet(radius, precision, interactive)
                    logger.info(f"倒角后顶点数: {len(processed_frame.get_vertices())}")
                else:
                    logger.info("圆弧倒角半径为0，不执行倒角")
            elif fillet_type == "adaptive":
                convex_radius = fillet_config.get("convex_radius", 0)
                concave_radius = fillet_config.get("concave_radius", 0)
                if convex_radius > 0 or concave_radius > 0:
                    # 根据zoom_config调整半径
                    if isinstance(zoom_config, (int, float)) and zoom_config != 0:
                        # 对于向外扩展(zoom_config > 0)，凸角半径增加，凹角半径减少
                        # 对于向内收缩(zoom_config < 0)，凸角半径减少，凹角半径增加
                        adjusted_convex_radius = convex_radius + zoom_config
                        adjusted_concave_radius = concave_radius - zoom_config
                        logger.info(f"应用调整后的自适应倒角: 凸角半径={adjusted_convex_radius}, 凹角半径={adjusted_concave_radius}, 精度={precision}")
                        processed_frame = processed_frame.apply_adaptive_fillet(adjusted_convex_radius, adjusted_concave_radius, precision, interactive)
                    else:
                        logger.info(f"应用自适应倒角: 凸角半径={convex_radius}, 凹角半径={concave_radius}, 精度={precision}")
                        processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                    logger.info(f"自适应倒角后顶点数: {len(processed_frame.get_vertices())}")
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
    def create_rings(cls, initial_frame: Frame, ring_width: Union[float, List[float]], ring_space: Union[float, List[float]], 
                   ring_num: int, fillet_config: dict = None, zoom_config: Union[int, float] = 0):
        """从 Frame 对象创建多个环
        
        参数:
            initial_frame: 初始 Frame 对象
            ring_width: 环宽度，可以是单一值或列表（每个环单独指定宽度）
            ring_space: 环间距，可以是单一值或列表（每个环单独指定间距）
            ring_num: 环数量
            fillet_config: 倒角配置字典
            zoom_config: 缩放值（正值表示向外扩展，负值表示向内收缩）
            
        返回:
            Region: 包含所有环的 Region 对象
        """
        logger.info(f"创建多边形环: 宽度={ring_width}, 间距={ring_space}, 环数={ring_num}")
        logger.info(f"环倒角配置: {fillet_config}")
        logger.info(f"环缩放配置: {zoom_config}")

        # 确保初始 Frame 是逆时针的
        initial_frame.ensure_counterclockwise()
        logger.debug(f"初始Frame顶点已确保为逆时针: {initial_frame.get_vertices()}")

        # 1. 处理缩放，获得新的初始Frame以及ring_width和ring_space
        if isinstance(zoom_config, (int, float)) and zoom_config != 0:
            logger.info(f"根据缩放配置: {zoom_config}，对初始Frame进行缩放，并调整ring_width和ring_space: {ring_width}, {ring_space}")
            initial_frame = initial_frame.offset(-zoom_config)
            if isinstance(ring_width, list):  ring_width = [width + 2 * zoom_config for width in ring_width]
            else:  ring_width = ring_width + 2 * zoom_config
            if isinstance(ring_space, list):  ring_space = [space - 2 * zoom_config for space in ring_space]
            else:  ring_space = ring_space - 2 * zoom_config
        else:
            logger.info(f"无需缩放")
            

        # 2. 生成所有环的边界Frame列表
        outer_frames = []  # 存储所有外边界Frame
        inner_frames = []  # 存储所有内边界Frame
        current_frame = initial_frame

        raw_ring_width = ring_width
        raw_ring_space = ring_space
        
        try:
            for i in range(ring_num):
                # 如果raw_ring_width和raw_ring_space是列表，则取列表中的值，否则取原始值
                if isinstance(raw_ring_width, list):  ring_width = raw_ring_width[i]
                else:  ring_width = raw_ring_width
                if isinstance(raw_ring_space, list):  ring_space = raw_ring_space[i]
                else:  ring_space = raw_ring_space

                # 生成内边界（当前frame就是内边界）
                inner_frames.append(current_frame)

                # 生成外边界
                outer_frame = current_frame.offset(ring_width)
                outer_frames.append(outer_frame)
                
                # 为下一个环准备起始frame
                current_frame = outer_frame.offset(ring_space)

        except Exception as e:
            logger.error(f"创建环的frame失败: {e}", exc_info=True)

        # 3. 对每个边界Frame应用缩放和倒角
        # 读取配置
        if fillet_config and fillet_config.get("type"):
            fillet_type = fillet_config["type"]
            precision = fillet_config.get("precision", 0.01)
            interactive = fillet_config.get("interactive", True)
            if "radius_list" in fillet_config:
                inner_radius = fillet_config.get("radius_list")
                logger.info(f"使用半径列表进行倒角: {inner_radius}")
            else:
                inner_radius = fillet_config.get("radius")
                logger.info(f"使用单一半径进行倒角: {inner_radius}")
            fillet_flag = True
        else:
            logger.info(f"无需倒角，skip。。。。。。")
            fillet_flag = False

        processed_outer_frames = []
        processed_inner_frames = []
        
        # 外边界倒角和缩放
        i = -1
        for processed_frame in outer_frames:
            i += 1

            # 如果raw_ring_width和raw_ring_space是列表，则取列表中的值，否则取原始值
            if isinstance(raw_ring_width, list):  ring_width = raw_ring_width[i]    
            else:  ring_width = raw_ring_width
            if isinstance(raw_ring_space, list):  ring_space = raw_ring_space[i]
            else:  ring_space = raw_ring_space
            
            # 应用倒角
            if fillet_flag:
                if fillet_type == "arc":
                    if isinstance(inner_radius, list):
                        convex_radius = [radius - zoom_config + ring_width for radius in inner_radius]
                        concave_radius = [radius + zoom_config - ring_width for radius in inner_radius]
                        logger.info(f"外边界使用半径列表进行倒角")
                    else:
                        convex_radius = inner_radius - zoom_config + ring_width
                        concave_radius = inner_radius + zoom_config - ring_width
                        logger.info(f"外边界使用单一半径进行倒角: {convex_radius}, {concave_radius}")  
                    processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                elif fillet_type == "adaptive":
                    convex_radius = fillet_config.get("convex_radius") 
                    concave_radius = fillet_config.get("concave_radius")
                    if convex_radius > 0 or concave_radius > 0:
                        processed_frame = processed_frame.apply_adaptive_fillet(convex_radius+ring_width, concave_radius - ring_width, precision, interactive)
            else:
                logger.info(f"外边界无需倒角，skip。。。。。。")
            
            processed_outer_frames.append(processed_frame)
        
        # 内边界倒角
        for processed_frame in inner_frames:
            # 应用倒角
            if fillet_flag:
                if fillet_type == "arc":
                    if isinstance(inner_radius, list):
                        convex_radius = [radius - zoom_config for radius in inner_radius]
                        concave_radius = [radius + zoom_config for radius in inner_radius]
                        logger.info(f"外边界使用半径列表进行倒角")
                    else:
                        convex_radius = inner_radius - zoom_config
                        concave_radius = inner_radius + zoom_config
                    processed_frame = processed_frame.apply_adaptive_fillet(convex_radius, concave_radius, precision, interactive)
                elif fillet_type == "adaptive":
                    convex_radius = fillet_config.get("convex_radius")
                    concave_radius = fillet_config.get("concave_radius")
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
        
        
        return result_region 