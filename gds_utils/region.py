import klayout.db as db
import numpy as np
import math
from .frame import Frame
from .utils import logger, um_to_db
from .ring_utils import RingRadiusProfile
from typing import Union, List, Optional

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
            preserve_radius_list = fillet_config.get("preserve_radius_list", False)

            # 确保帧是逆时针的，这对于某些倒角逻辑（如凹凸判断）可能很重要
            # Frame的倒角方法内部似乎没有强制，但作为最佳实践，在这里处理
            # 注意: apply_arc_fillet/apply_adaptive_fillet 返回新的Frame实例
            original_vertices_before_ccw_check = processed_frame.get_vertices() # 备份，以防万一
            processed_frame.ensure_counterclockwise() 
            if processed_frame.get_vertices() != original_vertices_before_ccw_check:
                logger.debug("Frame 顶点已转换为逆时针顺序")

            if fillet_type == "arc":
                radius = fillet_config.get("radius", 0)
                radius_list = fillet_config.get("radius_list", [])
                if radius != 0 or len(radius_list) > 0:
                    # 检查是否存在半径列表
                    if "radius_list" in fillet_config:
                        radius_list = fillet_config.get("radius_list")
                        # 根据zoom_config调整半径列表
                        if isinstance(zoom_config, (int, float)) and zoom_config != 0 and not preserve_radius_list:
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
                     ring_num: int, fillet_config: dict = None, zoom_config: Union[int, float] = 0,
                     inner_zoom: Optional[Union[int, float]] = None, outer_zoom: Optional[Union[int, float]] = None,
                     ring_radius_profile: Optional[RingRadiusProfile] = None,
                     preserve_radius_list: bool = False) -> 'Region':
        """从 Frame 对象创建多个环

        参数:
            initial_frame: 初始 Frame 对象
            ring_width: 环宽度，可以是单一值或列表（每个环单独指定宽度）
            ring_space: 环间距，可以是单一值或列表（每个环单独指定间距）
            ring_num: 环数量
            fillet_config: 倒角配置字典
            zoom_config: 统一缩放值（正值向外扩展，负值向内收缩），与旧逻辑保持兼容
            inner_zoom: 对内边界额外施加的缩放调整量（delta），None 表示沿用旧逻辑
            outer_zoom: 对外边界额外施加的缩放调整量（delta），None 表示沿用旧逻辑

        返回:
            Region: 包含所有环的 Region 对象
        """
        logger.info(f"创建多边形环: 宽度={ring_width}, 间距={ring_space}, 环数={ring_num}")
        logger.info(f"环倒角配置: {fillet_config}")
        logger.info(f"环缩放配置: {zoom_config}")
        logger.info(f"环内外独立缩放配置: inner_zoom={inner_zoom}, outer_zoom={outer_zoom}")

        initial_frame.ensure_counterclockwise()
        base_vertices = [tuple(pt) for pt in initial_frame.get_vertices()]
        if not base_vertices:
            logger.error("初始 Frame 顶点为空，无法生成环结构")
            return cls()
        logger.debug(f"初始Frame顶点已确保为逆时针: {base_vertices}")

        if ring_num <= 0:
            logger.warning("环数量小于等于0，返回空 Region")
            return cls()

        if isinstance(zoom_config, (int, float)):
            zoom_value = float(zoom_config)
        else:
            logger.warning(f"缩放配置类型异常({type(zoom_config)}), 按0处理")
            zoom_value = 0.0

        inner_adjust = float(inner_zoom) if inner_zoom is not None else 0.0
        outer_adjust = float(outer_zoom) if outer_zoom is not None else 0.0
        logger.debug(f"环额外缩放调整: inner_adjust={inner_adjust}, outer_adjust={outer_adjust}")

        def _normalize_sequence(value, length, name, default=0.0):
            if isinstance(value, list):
                seq = [float(v) for v in value]
                if len(seq) < length:
                    logger.warning(f"{name} 列表长度不足 {length}，使用最后一个值填充剩余部分")
                    if not seq:
                        seq = [default] * length
                    else:
                        seq.extend([seq[-1]] * (length - len(seq)))
                return seq
            try:
                scalar = float(value)
            except (TypeError, ValueError):
                logger.error(f"{name} 配置无法解析为数值，使用默认值 {default}")
                scalar = default
            return [scalar] * length

        ring_width_list = _normalize_sequence(ring_width, ring_num, "ring_width", default=0.0)
        ring_space_list = _normalize_sequence(ring_space, ring_num, "ring_space", default=0.0)

        if ring_radius_profile is not None:
            if len(ring_radius_profile.inner_series) != ring_num:
                raise ValueError(
                    f"ring_radius_profile 的 inner_series 长度({len(ring_radius_profile.inner_series)})与 ring_num({ring_num}) 不一致"
                )
            if ring_radius_profile.outer_series is not None and len(ring_radius_profile.outer_series) != ring_num:
                raise ValueError(
                    f"ring_radius_profile 的 outer_series 长度({len(ring_radius_profile.outer_series)})与 ring_num({ring_num}) 不一致"
                )

        result_region = cls()
        offset_accumulator = 0.0

        for idx in range(ring_num):
            width = ring_width_list[idx]
            if width <= 0:
                logger.warning(f"环 {idx + 1}: 宽度({width}) 非正值，跳过生成")
                space_after = ring_space_list[idx] if idx < len(ring_space_list) else 0.0
                offset_accumulator += max(space_after, 0.0)
                continue

            baseline_inner = offset_accumulator - zoom_value
            effective_width = width + 2 * zoom_value
            baseline_outer = baseline_inner + effective_width
            inner_offset = baseline_inner + inner_adjust
            outer_offset = baseline_outer + outer_adjust

            if outer_offset <= inner_offset:
                logger.error(
                    f"环 {idx + 1}: 外边界缩放({outer_offset}) 不大于内边界({inner_offset})，跳过此环")
                space_after = ring_space_list[idx] if idx < len(ring_space_list) else 0.0
                offset_accumulator += width + max(space_after, 0.0)
                continue

            try:
                ring_frame = Frame(base_vertices)

                fillet_for_ring_inner = fillet_config
                fillet_for_ring_outer = fillet_config
                if fillet_config and fillet_config.get("type") == "arc":
                    if ring_radius_profile is not None:
                        inner_radius_list = ring_radius_profile.inner_series[idx]
                        outer_radius_list = (
                            ring_radius_profile.outer_series[idx]
                            if ring_radius_profile.outer_series is not None
                            else ring_radius_profile.inner_series[idx]
                        )

                        fillet_for_ring_inner = dict(fillet_config)
                        fillet_for_ring_inner["radius_list"] = list(inner_radius_list)
                        if ring_radius_profile.preserve_inner or preserve_radius_list:
                            fillet_for_ring_inner["preserve_radius_list"] = True
                        else:
                            fillet_for_ring_inner.pop("preserve_radius_list", None)

                        fillet_for_ring_outer = dict(fillet_config)
                        fillet_for_ring_outer["radius_list"] = list(outer_radius_list)
                        if ring_radius_profile.preserve_outer or preserve_radius_list:
                            fillet_for_ring_outer["preserve_radius_list"] = True
                        else:
                            fillet_for_ring_outer.pop("preserve_radius_list", None)
                    elif "radius_list" in fillet_config:
                        fillet_for_ring_inner = dict(fillet_config)
                        fillet_for_ring_inner["radius_list"] = list(fillet_config["radius_list"])
                        fillet_for_ring_outer = dict(fillet_for_ring_inner)

                    if preserve_radius_list and ring_radius_profile is None:
                        fillet_for_ring_inner = dict(fillet_for_ring_inner)
                        fillet_for_ring_inner["preserve_radius_list"] = True
                        fillet_for_ring_outer = dict(fillet_for_ring_outer)
                        fillet_for_ring_outer["preserve_radius_list"] = True

                ring_region = cls.polygon2ring(
                    ring_frame,
                    inner_zoom=inner_offset,
                    outer_zoom=outer_offset,
                    fillet_config=fillet_config,
                    inner_fillet_config=fillet_for_ring_inner,
                    outer_fillet_config=fillet_for_ring_outer,
                )
                result_region.kdb_region += ring_region.get_klayout_region()
                logger.debug(
                    f"环 {idx + 1}: baseline_inner={baseline_inner}, baseline_outer={baseline_outer}, "
                    f"inner_offset={inner_offset}, outer_offset={outer_offset}")
            except Exception as exc:
                logger.error(f"环 {idx + 1}: 通过 polygon2ring 生成失败: {exc}", exc_info=True)

            space_after = ring_space_list[idx] if idx < len(ring_space_list) else 0.0
            offset_accumulator += width + space_after

        logger.info(f"已完成环的处理和合并，创建了 {ring_num} 个环")
        return result_region

    @classmethod
    def polygon2ring(cls, frame: Frame, inner_zoom: Union[int, float], outer_zoom: Union[int, float],
                     fillet_config: dict = None, inner_fillet_config: dict = None,
                     outer_fillet_config: dict = None) -> 'Region':
        """从Frame创建一个环结构，主要用于溅铝、刻孔工艺
        
        参数:
            frame: Frame对象，包含多边形的顶点
            inner_zoom: 内部缩放值（正值表示向外扩展，负值表示向内收缩）
            outer_zoom: 外部缩放值（正值表示向外扩展，负值表示向内收缩）
            fillet_config: 倒角配置字典
            
        返回:
            Region: 包含via结构的Region对象
        """
        logger.info(f"[Via开始] 内部缩放={inner_zoom}, 外部缩放={outer_zoom}")

        # 创建外部区域
        outer_config = outer_fillet_config if outer_fillet_config is not None else fillet_config
        inner_config = inner_fillet_config if inner_fillet_config is not None else fillet_config

        outer_region = cls.create_polygon(frame, outer_config, outer_zoom)
        outer_kdbregion = outer_region.get_klayout_region()
        logger.info(f"[外部区域] 多边形数={outer_kdbregion.count()}, 是否为空={outer_kdbregion.is_empty()}")

        # 创建内部区域
        inner_region = cls.create_polygon(frame, inner_config, inner_zoom)
        inner_kdbregion = inner_region.get_klayout_region()
        logger.info(f"[内部区域] 多边形数={inner_kdbregion.count()}, 是否为空={inner_kdbregion.is_empty()}")

        # 使用布尔减法得到via环
        result = outer_region - inner_region
        result_kdbregion = result.get_klayout_region()

        # ⭐ 关键诊断日志
        if result_kdbregion.is_empty():
            logger.error(f"❌ VIA失效: 布尔减法结果为空！outer={outer_kdbregion.count()}, inner={inner_kdbregion.count()}")
        else:
            logger.info(f"✓ VIA成功: 布尔减法得到{result_kdbregion.count()}个多边形")

        logger.info("[Via结束]")
        return result 
