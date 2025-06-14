import yaml
import sys
import os
import math # 需要 math 来生成五角星
from gds_utils import GDS, Frame, Region
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
        for pair in vertices_str.split(':'):
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
    
    # 创建GDS对象
    gds = GDS(
        input_file=gds_config.get('input_file'),
        cell_name=gds_config.get('cell_name', 'TOP'),
        layer_info=tuple(gds_config.get('default_layer', [1, 0])),
        dbu=global_config.get('dbu', 0.001)
    )
    
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
        
        # 创建 Frame
        frame = Frame(vertices)
        # ensure_counterclockwise() 现在由 Region 类的 create_polygon/create_rings 内部更好地处理
        
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
        if fillet_config and "interactive" not in fillet_config: # 从全局配置继承interactive
            fillet_config["interactive"] = global_config.get('fillet', {}).get('interactive', True)
        
        # 添加对倒角半径列表的支持
        if fillet_config and fillet_config.get("type") == "arc":
            # 如果提供了倒角半径列表，则使用它替代单一半径
            if "radii" in fillet_config:
                logger.info(f"检测到倒角半径列表: {fillet_config['radii']}")
                fillet_config["radius_list"] = fillet_config["radii"]
                # 保留radius作为默认半径，以防顶点数量与半径列表长度不匹配
                if "radius" not in fillet_config:
                    fillet_config["radius"] = 1.0  # 设置默认值
        
        logger.debug(f"形状 '{shape_name}' 的倒角配置: {fillet_config}")

        # 获取缩放配置
        zoom_config = shape_data.get('zoom', [0, 0])
        logger.debug(f"形状 '{shape_name}' 的缩放配置: {zoom_config}")

        region_obj = None # 重命名 region 为 region_obj

        if shape_data.get('type') == 'polygon':
            region_obj = Region.create_polygon(
                frame,
                fillet_config=fillet_config,
                zoom_config=zoom_config
            )
        elif shape_data.get('type') == 'rings':
            # 预处理ring_width，如果为, 代表一组生成规则，解析后转换为列表
            # 例如，((1, 5, 3), (6,11, 2))对应[3,3,3,3,3,2,2,2,2,2,2]
            print(f"ring_width的raw type是: {type(shape_data.get('ring_width'))}")
            ring_width_rule = ast.literal_eval(shape_data.get('ring_width'))
            if isinstance(ring_width_rule, list) and isinstance(ring_width_rule[0], tuple):
                logger.info(f"ring_width是list，且第一个元素是tuple。试图根据规则生成ring_width列表")
                ring_width_list = []
                # 校验ring_width的规则是否合规，正确的规则是：
                # 1. 每个元素ring_width_rule[i]必须是tuple，且长度为3
                # 2. ring_width_rule[i][1] = ring_width_rule[i+1][0]+1, 除非是最后一个元素
                # 3. ring_width_rule[i][0] < ring_width_rule[i][1]
                logger.info(f"ring_width_rule: {ring_width_rule}")
                for i in range(len(ring_width_rule)-1):
                    if not isinstance(ring_width_rule[i], tuple) or len(ring_width_rule[i]) != 3:
                        logger.error(f"rule error1: ring_width的规则{ring_width_rule}格式错误，必须为tuple，且长度为3")
                        print(f"ring_width_rule[i]: {ring_width_rule[i]}, {i}")
                        return
                    if not isinstance(ring_width_rule[i+1], tuple) or len(ring_width_rule[i+1]) != 3:
                        logger.error(f"rule error2: ring_width的规则{ring_width_rule}格式错误，必须为tuple，且长度为3")
                        return
                    #if ring_width_rule[i][1] != ring_width_rule[i+1][0]+1:
                    #    logger.error(f"ring_width的规则{ring_width_rule}格式错误，必须满足ring_width_rule[i][1] = ring_width_rule[i+1][0]+1")
                    #     return
                    #if ring_width_rule[i][0] >= ring_width_rule[i][1]:
                    #    logger.error(f"ring_width的规则{ring_width_rule}格式错误，必须满足ring_width_rule[i][0] < ring_width_rule[i][1]")
                    #    return
                # 解析规则，生成ring_width_list
                for rule in ring_width_rule:
                    logger.info(f"rule: {rule}")
                    ring_width_list += [rule[2]] * (rule[1] - rule[0] + 1)
                shape_data['ring_width'] = ring_width_list  # 将处理后的ring_width列表赋值给shape_data
            #logger.info(f"处理后的ring_width列表: {ring_width_list}")
            elif isinstance(ring_width_rule, tuple):
                ring_width_list = list(ring_width_rule)
                shape_data['ring_width'] = ring_width_list  # 将处理后的ring_width列表赋值给shape_data
                logger.info(f"转换ring_width输入列表为list: {ring_width_list}")
            elif isinstance(ring_width_rule, (int, float)):
                ring_width = float(ring_width_rule)
                shape_data['ring_width'] = ring_width  # 将处理后的ring_width列表赋值给shape_data
                logger.info(f"ring_width输入为单值，转换为list: {ring_width}")
            else:
                logger.error(f"ring_width输入格式错误，只能接收list或tuple或int/float，当前类型: {type(ring_width_rule)}")
                return
            logger.info(f"处理后的ring_width: {shape_data['ring_width']}")

            # 处理ring_space
            print(f"ring_space的raw type是: {type(shape_data.get('ring_space'))}")
            ring_space_rule = ast.literal_eval(shape_data.get('ring_space'))
            if isinstance(ring_space_rule, list) and isinstance(ring_space_rule[0], tuple):
                logger.info(f"ring_space是list，且第一个元素是list。试图根据规则生成ring_space列表")
                ring_space_list = []
                # 校验ring_width的规则是否合规，正确的规则是：
                # 1. 每个元素ring_width_rule[i]必须是tuple，且长度为3
                # 2. ring_width_rule[i][1] = ring_width_rule[i+1][0], 除非是最后一个元素
                # 3. ring_width_rule[i][0] < ring_width_rule[i][1]
                for i in range(len(ring_space_rule)-1):
                    if not isinstance(ring_space_rule[i], tuple) or len(ring_space_rule[i]) != 3:
                        logger.error(f"ring_space的规则{ring_space_rule[i]}格式错误，必须为tuple，且长度为3")
                        return
                    if not isinstance(ring_space_rule[i+1], tuple) or len(ring_space_rule[i+1]) != 3:
                        logger.error(f"ring_space的规则{ring_space_rule[i]}格式错误，必须为tuple，且长度为3")
                        return
                    #if ring_space_rule[i][1] != ring_space_rule[i+1][0]:
                    #    logger.error(f"ring_space的规则{ring_space_rule}格式错误，必须满足ring_space_rule[i][1] = ring_space_rule[i+1][0]")
                    #    return
                    #if ring_space_rule[i][0] >= ring_space_rule[i][1]:
                    #    logger.error(f"ring_space的规则{ring_space_rule}格式错误，必须满足ring_space_rule[i][0] < ring_space_rule[i][1]")
                    #    return
                # 解析规则，生成ring_space_list
                for rule in ring_space_rule:
                    ring_space_list+=[rule[2]] * (rule[1] - rule[0])
                shape_data['ring_space'] = ring_space_list  # 将处理后的ring_space列表赋值给shape_data
            elif isinstance(ring_space_rule, tuple):
                ring_space_list = list(ring_space_rule)
                shape_data['ring_space'] = ring_space_list  # 将处理后的ring_space列表赋值给shape_data
                logger.info(f"转换ring_space输入列表为list: {ring_space_list}")
            elif isinstance(ring_space_rule, (int, float)):
                ring_space = float(ring_space_rule)
                shape_data['ring_space'] = ring_space  # 将处理后的ring_space列表赋值给shape_data
                logger.info(f"ring_space输入为单值，转换为float: {ring_space}")
            else:
                logger.error(f"ring_space输入格式错误，只能接收list或tuple，当前类型: {type(ring_space_rule)}")
                return
            logger.info(f"处理后的ring_space列表: {shape_data['ring_space']}")
            
            region_obj = Region.create_rings(
                frame,
                ring_width=shape_data.get('ring_width'),
                ring_space=shape_data.get('ring_space'),
                ring_num=shape_data.get('ring_num'),
                fillet_config=fillet_config,
                zoom_config=zoom_config 
            )
        elif shape_data.get('type') == 'via':
            region_obj = Region.polygon2ring(
                frame,
                inner_zoom=shape_data.get('inner_zoom', -1),
                outer_zoom=shape_data.get('outer_zoom', 1),
                fillet_config=fillet_config
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