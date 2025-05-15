import logging
import os

# 初始化全局logger变量
logger = logging.getLogger("gds_utils")
# 设置一个默认的NullHandler，避免"No handler found"警告
logger.addHandler(logging.NullHandler())

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

def um_to_db(v):
    """单位转换函数（微米转数据库单位）"""
    return int(float(v) * 1000) 