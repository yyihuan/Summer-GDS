import yaml
import sys
import os
import math # 需要 math 来生成五角星
import copy
from gds_utils import GDS, Frame, Region
from gds_utils.fillet_utils import normalize_arc_fillet_config, resolve_via_fillet_configs
from gds_utils.ring_utils import build_ring_radius_series
from gds_utils.utils import setup_logging, logger
import klayout.db as db  # 添加这行导入
import ast

# 新增的辅助函数
def _generate_vertices(gen_config: dict) -> list:
    """根据配置生成顶点列表"""
    shape_type = gen_config.get("shape_type")
    vertices = []
    if shape_type == "star":
        center_x = gen_config.get("center_x", 0)
        center_y = gen_config.get("center_y", 0)
        outer_radius = gen_config.get("outer_radius", 10)
        inner_radius = gen_config.get("inner_radius", 5)
        num_points = gen_config.get("points", 5)
        
        if num_points < 2:
            logger.warning(f"星形点数 ({num_points}) 过少，至少需要2个点。")
            return []

        for i in range(num_points * 2):
            angle = math.pi / num_points * i - math.pi / 2 # 调整起始角度使尖端向上
            radius = outer_radius if i % 2 == 0 else inner_radius
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            vertices.append((x, y))
        logger.info(f"生成 {num_points}角星顶点，中心:({center_x},{center_y}), 外径:{outer_radius}, 内径:{inner_radius}")

    # 可以扩展以支持其他形状类型，如 "rectangle", "circle" 等
    # elif shape_type == "rectangle":
    #     pass 
    else:
        logger.warning(f"未知的顶点生成类型: {shape_type}")
    return vertices



def parse_vertices(vertices_str: str) -> list:
    """解析顶点字符串
    
    参数:
        vertices_str: 顶点字符串，格式为 "x1,y1:x2,y2:..."
        
    返回:
        list: 顶点列表 [(x1,y1), (x2,y2), ...]
    """
    try:
        vertices = []
        for pair in vertices_str.split(';'):
            x, y = map(float, pair.split(','))
            vertices.append((float(x), float(y)))  # 确保是浮点数
        
        # 检查顶点数量
        if len(vertices) < 3:
            logger.error(f"顶点数量不足: {len(vertices)}")
            return []
            
        # 检查并修正顶点顺序（确保逆时针）
        def is_counterclockwise(pts):
            area = 0
            for i in range(len(pts)):
                j = (i + 1) % len(pts)
                area += pts[i][0] * pts[j][1]
                area -= pts[j][0] * pts[i][1]
            return area > 0
            
        if not is_counterclockwise(vertices):
            logger.info("检测到顺时针顶点顺序，正在修正为逆时针")
            vertices.reverse()
            
        return vertices
    except Exception as e:
        logger.error(f"解析顶点失败: {e}")
        return []

def main():
    """主函数"""
    # 首先设置日志
    setup_logging(True)  # 显示日志
    
    # 解析命令行参数
    if len(sys.argv) < 2:
        print("用法: python main_oop.py <config.yaml>")
        return
    
    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        print(f"配置文件不存在: {config_file}")
        return
    
    # 加载配置
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"加载配置文件: {config_file}")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return
    
    # 获取全局配置
    global_config = config.get('global', {})
    gds_config = config.get('gds', {})
    shapes_config = config.get('shapes', [])

    # 提取 dbu 和 precision 参数
    dbu = global_config.get('dbu', 0.001)
    precision = global_config.get('precision')
    logger.info(f"从 YAML 读取参数：dbu={dbu} μm, precision={precision} μm")

    # 创建GDS对象（验证会在 GDS.__init__ 中进行）
    gds = GDS(
        input_file=gds_config.get('input_file'),
        cell_name=gds_config.get('cell_name', 'TOP'),
        layer_info=tuple(gds_config.get('default_layer', [1, 0])),
        dbu=dbu,
        precision=precision
    )
    
    shape_fillet_registry = {}

    # 处理每个形状
    for shape_data in shapes_config: # 重命名 `shape` 为 `shape_data`
        shape_name = shape_data.get('name', f"Unnamed_{shape_data.get('type')}")
        logger.info(f"处理形状: {shape_name} (类型: {shape_data.get('type')})")
        
        vertices = []
        if "vertices_gen" in shape_data:
            logger.debug(f"使用 vertices_gen 生成 '{shape_name}' 的顶点: {shape_data['vertices_gen']}")
            vertices = _generate_vertices(shape_data["vertices_gen"])
        elif "vertices" in shape_data:
            logger.debug(f"从 vertices 字符串解析 '{shape_name}' 的顶点: {shape_data['vertices']}")
            vertices = parse_vertices(shape_data.get('vertices', ''))
        
        if not vertices:
            logger.error(f"形状 '{shape_name}' 的顶点数据无效或生成失败，跳过此形状")
            continue

        # 创建 Frame 时传递 precision 参数
        frame = Frame(vertices, precision=precision)
        
        # 获取或创建目标单元格
        cell_name = shape_data.get('cell', gds_config.get('cell_name', 'TOP'))
        cell = gds.get_cell(cell_name)
        if cell is None:
            cell = gds.create_cell(cell_name)
        
        # 获取图层信息
        layer_info_val = shape_data.get('layer', gds_config.get('default_layer', [1, 0]))
        if isinstance(layer_info_val, str) and cell:
            logger.warning(f"图层名称 '{layer_info_val}' 的解析逻辑尚未完全实现，请确保它已在mapping中或通过序号指定。暂时使用默认图层。")
            layer_info = tuple(gds_config.get('default_layer', [1, 0]))
        elif isinstance(layer_info_val, list):
             layer_info = tuple(layer_info_val)
        else:
            logger.error(f"未知的图层格式: {layer_info_val} for shape {shape_name}. 使用默认图层。")
            layer_info = tuple(gds_config.get('default_layer', [1, 0]))

        # 提取倒角配置
        fillet_config = shape_data.get('fillet')
        if fillet_config and "interactive" not in fillet_config:  # 从全局配置继承interactive
            fillet_config["interactive"] = global_config.get('fillet', {}).get('interactive', True)

        shape_type = shape_data.get('type')
        ring_num_hint = shape_data.get('ring_num') if shape_type == 'rings' else None
        allow_inner_outer_split = shape_type == 'via'
        fillet_config = normalize_arc_fillet_config(
            shape_name,
            fillet_config,
            vertex_count=len(frame.get_vertices()),
            ring_num_hint=ring_num_hint,
            allow_inner_outer_split=allow_inner_outer_split,
        )

        logger.debug(f"形状 '{shape_name}' 的倒角配置: {fillet_config}")

        shape_id = shape_data.get('id')
        if shape_id:
            stored_fillet = copy.deepcopy(fillet_config) if fillet_config else None
            shape_fillet_registry[shape_id] = stored_fillet

        # 获取缩放配置
        zoom_raw = shape_data.get('zoom', 0)
        if isinstance(zoom_raw, (int, float)):
            zoom_config = float(zoom_raw)
        elif isinstance(zoom_raw, list) and zoom_raw:
            first_val = zoom_raw[0]
            if isinstance(first_val, (int, float)):
                zoom_config = float(first_val)
            else:
                logger.warning(f"形状 '{shape_name}' 的缩放配置列表首项不是数值，使用默认0")
                zoom_config = 0.0
        else:
            if zoom_raw not in (None,):
                logger.warning(f"形状 '{shape_name}' 的缩放配置格式不正确，应为数值，当前类型: {type(zoom_raw)}")
            zoom_config = 0.0
        logger.debug(f"形状 '{shape_name}' 的缩放配置: {zoom_config}")

        # rings 专用缩放配置
        inner_zoom_val = shape_data.get('inner_zoom')
        outer_zoom_val = shape_data.get('outer_zoom')

        def _parse_optional_zoom(value, label):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            logger.error(f"形状 '{shape_name}' 的 {label} 格式错误，期望数值类型，已忽略。实际类型: {type(value)}")
            return None

        inner_zoom_config = _parse_optional_zoom(inner_zoom_val, "inner_zoom")
        outer_zoom_config = _parse_optional_zoom(outer_zoom_val, "outer_zoom")

        inner_zoom_effective = inner_zoom_config if inner_zoom_config is not None else None
        outer_zoom_effective = outer_zoom_config if outer_zoom_config is not None else None

        logger.debug(
            f"形状 '{shape_name}' 的内外缩放配置: inner_zoom="
            f"{inner_zoom_effective if inner_zoom_effective is not None else '默认'}, "
            f"outer_zoom={outer_zoom_effective if outer_zoom_effective is not None else '默认'}")

        region_obj = None # 重命名 region 为 region_obj

        if shape_data.get('type') == 'polygon':
            region_obj = Region.create_polygon(
                frame,
                fillet_config=fillet_config,
                zoom_config=zoom_config
            )
        elif shape_data.get('type') == 'rings':
            ring_mode = shape_data.get('ring_mode', 'custom')
            if ring_mode not in {'custom', 'concentric'}:
                raise ValueError(f"形状 '{shape_name}' 的 ring_mode 非法: {ring_mode}")
            shape_data['ring_mode'] = ring_mode

            ring_num = shape_data.get('ring_num')
            if not isinstance(ring_num, int) or ring_num <= 0:
                raise ValueError(f"形状 '{shape_name}' 的 ring_num 无效: {ring_num}")

            # 预处理 ring_width，如果为规则字符串则解析后转换为列表
            ring_width_raw = shape_data.get('ring_width')
            ring_width_rule = None
            if isinstance(ring_width_raw, str):
                try:
                    ring_width_rule = ast.literal_eval(ring_width_raw)
                except (ValueError, SyntaxError) as exc:
                    logger.error(f"ring_width 字符串解析失败: {exc}")
                    continue
            else:
                ring_width_rule = ring_width_raw

            if ring_width_rule is None:
                raise ValueError(f"形状 '{shape_name}' 未提供 ring_width，无法生成环阵列")

            if isinstance(ring_width_rule, list):
                if not ring_width_rule:
                    raise ValueError(f"形状 '{shape_name}' 的 ring_width 列表为空")
                if isinstance(ring_width_rule[0], tuple):
                    logger.info(f"ring_width是list，且第一个元素是tuple。试图根据规则生成ring_width列表")
                    ring_width_list = []
                    logger.info(f"ring_width_rule: {ring_width_rule}")
                    for i in range(len(ring_width_rule)-1):
                        if not isinstance(ring_width_rule[i], tuple) or len(ring_width_rule[i]) != 3:
                            raise ValueError(f"ring_width 规则格式错误: {ring_width_rule[i]}")
                        if not isinstance(ring_width_rule[i+1], tuple) or len(ring_width_rule[i+1]) != 3:
                            raise ValueError(f"ring_width 规则格式错误: {ring_width_rule[i+1]}")
                    for rule in ring_width_rule:
                        if not isinstance(rule, tuple) or len(rule) != 3:
                            raise ValueError(f"ring_width 规则项格式错误: {rule}")
                        ring_width_list += [rule[2]] * (rule[1] - rule[0] + 1)
                    shape_data['ring_width'] = ring_width_list
                elif all(isinstance(val, (int, float)) for val in ring_width_rule):
                    shape_data['ring_width'] = [float(val) for val in ring_width_rule]
                else:
                    raise ValueError(f"形状 '{shape_name}' 的 ring_width 列表格式不支持: {ring_width_rule}")
            elif isinstance(ring_width_rule, tuple):
                ring_width_list = list(ring_width_rule)
                shape_data['ring_width'] = ring_width_list  # 将处理后的ring_width列表赋值给shape_data
                logger.info(f"转换ring_width输入列表为list: {ring_width_list}")
            elif isinstance(ring_width_rule, (int, float)):
                ring_width = float(ring_width_rule)
                shape_data['ring_width'] = ring_width  # 将处理后的ring_width列表赋值给shape_data
                logger.info(f"ring_width输入为单值，转换为list: {ring_width}")
            else:
                raise ValueError(f"ring_width输入格式错误，只能接收list或tuple或int/float，当前类型: {type(ring_width_rule)}")
            logger.info(f"处理后的ring_width: {shape_data['ring_width']}")

            # 处理ring_space
            ring_space_raw = shape_data.get('ring_space')
            if isinstance(ring_space_raw, str):
                try:
                    ring_space_rule = ast.literal_eval(ring_space_raw)
                except (ValueError, SyntaxError) as exc:
                    logger.error(f"ring_space 字符串解析失败: {exc}")
                    continue
            else:
                ring_space_rule = ring_space_raw

            if ring_space_rule is None:
                raise ValueError(f"形状 '{shape_name}' 未提供 ring_space，无法生成环阵列")

            if isinstance(ring_space_rule, list):
                if not ring_space_rule:
                    raise ValueError(f"形状 '{shape_name}' 的 ring_space 列表为空")
                if isinstance(ring_space_rule[0], tuple):
                    logger.info(f"ring_space是list，且第一个元素是tuple。试图根据规则生成ring_space列表")
                    ring_space_list = []
                    for i in range(len(ring_space_rule)-1):
                        if not isinstance(ring_space_rule[i], tuple) or len(ring_space_rule[i]) != 3:
                            raise ValueError(f"ring_space 规则格式错误: {ring_space_rule[i]}")
                        if not isinstance(ring_space_rule[i+1], tuple) or len(ring_space_rule[i+1]) != 3:
                            raise ValueError(f"ring_space 规则格式错误: {ring_space_rule[i+1]}")
                    for rule in ring_space_rule:
                        if not isinstance(rule, tuple) or len(rule) != 3:
                            raise ValueError(f"ring_space 规则项格式错误: {rule}")
                        ring_space_list += [rule[2]] * (rule[1] - rule[0])
                    shape_data['ring_space'] = ring_space_list
                elif all(isinstance(val, (int, float)) for val in ring_space_rule):
                    shape_data['ring_space'] = [float(val) for val in ring_space_rule]
                else:
                    raise ValueError(f"形状 '{shape_name}' 的 ring_space 列表格式不支持: {ring_space_rule}")
            elif isinstance(ring_space_rule, tuple):
                ring_space_list = list(ring_space_rule)
                shape_data['ring_space'] = ring_space_list  # 将处理后的ring_space列表赋值给shape_data
                logger.info(f"转换ring_space输入列表为list: {ring_space_list}")
            elif isinstance(ring_space_rule, (int, float)):
                ring_space = float(ring_space_rule)
                shape_data['ring_space'] = ring_space  # 将处理后的ring_space列表赋值给shape_data
                logger.info(f"ring_space输入为单值，转换为float: {ring_space}")
            else:
                raise ValueError(f"ring_space输入格式错误，只能接收list或tuple，当前类型: {type(ring_space_rule)}")
            logger.info(f"处理后的ring_space列表: {shape_data['ring_space']}")

            # 严格长度与数值校验
            def _finalize_ring_sequence(raw_value, label):
                seq = raw_value
                if isinstance(seq, (int, float)):
                    seq = [float(seq)] * ring_num
                elif isinstance(seq, list):
                    seq = [float(item) for item in seq]
                else:
                    raise ValueError(f"形状 '{shape_name}' 的 {label} 类型非法: {type(seq)}")

                if len(seq) == 1 and ring_num > 1:
                    seq = seq * ring_num
                if len(seq) != ring_num:
                    raise ValueError(f"形状 '{shape_name}' 的 {label} 长度({len(seq)})与 ring_num({ring_num}) 不一致")
                if any(val < 0 for val in seq):
                    raise ValueError(f"形状 '{shape_name}' 的 {label} 存在负值: {seq}")
                return seq

            ring_width_list_final = _finalize_ring_sequence(shape_data['ring_width'], 'ring_width')
            ring_space_list_final = _finalize_ring_sequence(shape_data['ring_space'], 'ring_space')

            shape_data['ring_width'] = ring_width_list_final
            shape_data['ring_space'] = ring_space_list_final

            ring_radius_profile = None
            if fillet_config and fillet_config.get('type') == 'arc':
                base_radius_list = fillet_config.get('radius_list')
                if base_radius_list is None:
                    raise ValueError(f"形状 '{shape_name}' 未提供 radius_list")

                zoom_params = {
                    'vertex_count': len(frame.get_vertices()),
                    'base_zoom': zoom_config,
                    'inner_adjust': inner_zoom_effective if inner_zoom_effective is not None else 0.0,
                    'outer_adjust': outer_zoom_effective if outer_zoom_effective is not None else 0.0,
                }

                ring_radius_profile = build_ring_radius_series(
                    mode=ring_mode,
                    base_radius_list=base_radius_list,
                    ring_width_list=ring_width_list_final,
                    ring_space_list=ring_space_list_final,
                    zoom_params=zoom_params,
                    ring_num=ring_num,
                )
            
            region_obj = Region.create_rings(
                frame,
                ring_width=shape_data.get('ring_width'),
                ring_space=shape_data.get('ring_space'),
                ring_num=shape_data.get('ring_num'),
                fillet_config=fillet_config,
                zoom_config=zoom_config,
                inner_zoom=inner_zoom_effective,
                outer_zoom=outer_zoom_effective,
                ring_radius_profile=ring_radius_profile,
                preserve_radius_list=False
            )
        elif shape_type == 'via':
            derivation_info = shape_data.get('derivation') or {}
            base_shape_id = derivation_info.get('base_shape_id')
            base_radius_list = None
            if base_shape_id:
                base_fillet = shape_fillet_registry.get(base_shape_id)
                if base_fillet and base_fillet.get('radius_list'):
                    base_radius_list = base_fillet.get('radius_list')

            inner_zoom_effective_via = shape_data.get('inner_zoom', -1)
            outer_zoom_effective_via = shape_data.get('outer_zoom', 1)
            try:
                inner_zoom_effective_via = float(inner_zoom_effective_via)
            except (TypeError, ValueError):
                inner_zoom_effective_via = -1.0
            try:
                outer_zoom_effective_via = float(outer_zoom_effective_via)
            except (TypeError, ValueError):
                outer_zoom_effective_via = 1.0

            zoom_delta = outer_zoom_effective_via - inner_zoom_effective_via

            via_base_fillet, via_inner_fillet, via_outer_fillet = resolve_via_fillet_configs(
                shape_name,
                fillet_config,
                base_radius_list=base_radius_list,
                zoom_delta=zoom_delta,
            )
            region_obj = Region.polygon2ring(
                frame,
                inner_zoom=shape_data.get('inner_zoom', -1),
                outer_zoom=shape_data.get('outer_zoom', 1),
                fillet_config=via_base_fillet,
                inner_fillet_config=via_inner_fillet,
                outer_fillet_config=via_outer_fillet
            )
        else:
            logger.error(f"形状 '{shape_name}' 的类型未知: {shape_data.get('type')}")
            continue
        
        # 添加到单元格
        if region_obj and not region_obj.get_klayout_region().is_empty():
            cell.add_region(region_obj, layer_info)
            logger.info(f"添加形状 '{shape_name}' 到单元格 '{cell_name}' 的图层 {layer_info}")
        elif region_obj and region_obj.get_klayout_region().is_empty():
            logger.warning(f"为形状 '{shape_name}' 创建的 Region 为空，未添加到GDS。可能由于倒角失败或顶点无效。")
        else:
            logger.error(f"未能为形状 '{shape_name}' 创建 Region 对象。")
    
    # 保存GDS文件
    output_file = gds_config.get('output_file', 'output.gds')
    save_mapping_config = global_config.get('layer_mapping', {})
    
    # 确保 mapping 文件名在 save_mapping 为 True 时被正确传递
    mapping_file_to_save = None
    if save_mapping_config.get('save', True): # 默认为 True
        mapping_file_to_save = save_mapping_config.get('file', 'layer_mapping.txt')

    gds.save(output_file, save_mapping=mapping_file_to_save) # 修改参数名
    logger.info(f"GDS文件已保存: {output_file}")
    if mapping_file_to_save:
        logger.info(f"图层映射文件已保存: {mapping_file_to_save}")

if __name__ == "__main__":
    main() 
