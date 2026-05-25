import klayout.db as db
from .layer import LayerManager
from .utils import logger

class Cell:
    """封装 KLayout Cell 对象的类"""
    
    def __init__(self, kdb_cell):
        """初始化 Cell 对象
        
        参数:
            kdb_cell: KLayout Cell 对象
        """
        self.kdb_cell = kdb_cell
        self.layer_manager = LayerManager()
        logger.debug(f"创建 Cell: {kdb_cell.name}")

    def get_layer_index(self, layer_info):
        """获取图层索引
        
        参数:
            layer_info: 图层信息元组 (layer_num, datatype)
            
        返回:
            int | None: 图层索引，不存在则返回None
        """
        return self.layer_manager.get_layer_index(layer_info)

    def create_layer(self, layer_info, layer_name=None):
        """创建或获取图层索引
        
        参数:
            layer_info: 图层信息元组 (layer_num, datatype)
            layer_name: 图层名称，可选
            
        返回:
            int: 图层索引
        """
        # 调用 LayerManager 的方法
        layer_index = self.layer_manager.create_layer(layer_info, layer_name)
        
        # 确保 KLayout 布局中存在该图层信息
        layer_num, datatype = layer_info
        layer_info_obj = db.LayerInfo(layer_num, datatype)
        
        # 获取或创建 KLayout 布局中的图层
        layout = self.kdb_cell.layout()
        if layout:
            kl_layer_index = layout.layer(layer_info_obj)
            logger.debug(f"KLayout 图层索引: {kl_layer_index} for {layer_info}")
            
            # 更新 LayerManager 中的索引以匹配 KLayout 的索引
            self.layer_manager.layer_indices[layer_info] = kl_layer_index
        
        return self.layer_manager.get_layer_index(layer_info)

    def add_region(self, region, layer_info):
        """向单元格添加区域
        
        参数:
            region: Region 对象
            layer_info: 图层信息元组 (layer_num, datatype)
        """
        try:
            # 确保存在图层
            layer_num, datatype = layer_info
            layout = self.kdb_cell.layout()
            if not layout:
                logger.error(f"无法获取 Cell {self.kdb_cell.name} 的布局")
                return
            
            # 创建或获取 KLayout 图层
            layer_info_obj = db.LayerInfo(layer_num, datatype)
            kl_layer_index = layout.layer(layer_info_obj)
            
            # 添加区域到图层
            self.kdb_cell.shapes(kl_layer_index).insert(region.get_klayout_region())
            
            # 同时更新 LayerManager 中的索引
            if layer_info not in self.layer_manager.layer_indices:
                self.layer_manager.layer_indices[layer_info] = kl_layer_index
                logger.debug(f"在 LayerManager 中添加图层索引映射: {layer_info} -> {kl_layer_index}")
                
            logger.debug(f"向 Cell {self.kdb_cell.name} 的图层 {layer_info} 添加区域")
        except Exception as e:
            logger.error(f"添加区域失败: {e}")

    def get_layer_manager(self):
        """获取图层管理器
        
        返回:
            LayerManager: 图层管理器对象
        """
        return self.layer_manager 