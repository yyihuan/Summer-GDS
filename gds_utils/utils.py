import logging
import os

# 初始化全局logger变量
logger = logging.getLogger("gds_utils")
# 设置一个默认的NullHandler，避免"No handler found"警告
logger.addHandler(logging.NullHandler())

# 全局dbu变量（可动态设置）
_current_dbu = 0.001

def setup_logging(show_log=True):
    """配置日志系统

    参数:
        show_log: 是否在控制台显示日志
    """
    global logger
    # 移除所有现有的handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handlers = [logging.FileHandler("gds_debug.log", mode='w')]
    if show_log:
        handlers.append(logging.StreamHandler())

    # 只用basicConfig配置handler，避免重复
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    logger.setLevel(logging.DEBUG)
    # 不再手动addHandler，避免重复日志

    # 降低matplotlib日志级别，防止findfont等DEBUG日志刷屏
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    return logger

def set_global_dbu(dbu_value):
    """设置全局dbu（在GDS初始化时调用）

    参数:
        dbu_value: 数据库单位（μm）
    """
    global _current_dbu
    _current_dbu = dbu_value
    logger.info(f"设置全局 dbu = {dbu_value} μm")

def get_global_dbu():
    """获取当前全局dbu

    返回:
        float: 当前的全局dbu值
    """
    return _current_dbu

def um_to_db(v):
    """单位转换函数（微米转数据库单位）

    参数:
        v: 微米值

    返回:
        int: 转换后的数据库单位值
    """
    global _current_dbu
    db_value = round(float(v) / _current_dbu)
    return int(db_value)

def validate_precision_dbu(precision, dbu):
    """验证 precision 和 dbu 的兼容性

    参数:
        precision: 精度（μm），可以为 None
        dbu: 数据库单位（μm）

    返回:
        bool: 验证通过返回 True

    抛出:
        ValueError: 不满足兼容性条件时抛出
    """
    if precision is None:
        return True

    # 检查范围
    if not (0.00001 <= dbu <= 1.0):
        raise ValueError(f"dbu 必须在 0.00001 ~ 1.0 范围内，当前值: {dbu}")

    if not (0.00001 <= precision <= 1.0):
        raise ValueError(f"precision 必须在 0.00001 ~ 1.0 范围内，当前值: {precision}")

    # 检查兼容性：precision / dbu 必须是整数
    ratio = precision / dbu
    if abs(ratio - round(ratio)) > 1e-10:
        raise ValueError(
            f"precision 和 dbu 不兼容：{precision} / {dbu} = {ratio}，"
            f"必须是整数倍关系！"
        )

    return True

def round_vertices(vertices, precision):
    """四舍五入顶点到指定精度

    参数:
        vertices: 顶点列表 [(x1,y1), (x2,y2), ...]
        precision: 精度（μm），None 表示不转换

    返回:
        list: 转换后的顶点列表
    """
    if precision is None:
        return list(vertices)

    rounded = []
    for x, y in vertices:
        x_rounded = round(x / precision) * precision
        y_rounded = round(y / precision) * precision
        rounded.append((x_rounded, y_rounded))

    logger.debug(f"顶点精度转换：precision={precision}, 点数={len(rounded)}")
    return rounded 