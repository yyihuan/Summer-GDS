import klayout.db as db
import os
from .cell import Cell
from .utils import logger

class GDS:
    """操作 GDS 文件的类"""
    
    def __init__(self, input_file=None, cell_name="TOP", layer_info=(1, 0), dbu=0.001):
        """初始化 GDS 对象
        
        参数:
            input_file: GDS 输入文件路径，如果为None则创建新的布局
            cell_name: 默认单元格名称
            layer_info: 默认图层信息 (layer_num, datatype)
            dbu: 数据库单位（默认0.001，即1纳米）
        """
        self.kdb_layout = db.Layout()
        self.cells = {}
        self.dbu = dbu
        
        # 设置数据库单位
        self.kdb_layout.dbu = dbu
        
        if input_file:
            try:
                # 读取现有GDS文件
                self.kdb_layout.read(input_file)
                logger.info(f"读取GDS文件: {input_file}")
                
                # 加载所有单元格
                for cell in self.kdb_layout.each_cell():
                    self.cells[cell.name] = Cell(cell)
                    logger.debug(f"加载单元格: {cell.name}")
                
            except Exception as e:
                logger.error(f"读取GDS文件失败: {e}")
                # 创建默认单元格
                self._create_default_cell(cell_name)
        else:
            # 创建默认单元格
            self._create_default_cell(cell_name)
    
    def _create_default_cell(self, cell_name):
        """创建默认单元格
        
        参数:
            cell_name: 单元格名称
        """
        try:
            kdb_cell = self.kdb_layout.create_cell(cell_name)
            self.cells[cell_name] = Cell(kdb_cell)
            logger.info(f"创建新单元格: {cell_name}")
        except Exception as e:
            logger.error(f"创建单元格失败: {e}")

    def get_cells(self):
        """获取所有单元格
        
        返回:
            list: Cell 对象列表
        """
        return list(self.cells.values())

    def get_cell(self, cell_name):
        """获取指定名称的单元格
        
        参数:
            cell_name: 单元格名称
            
        返回:
            Cell | None: 单元格对象，不存在则返回None
        """
        return self.cells.get(cell_name)

    def create_cell(self, cell_name):
        """创建新的单元格
        
        参数:
            cell_name: 单元格名称
            
        返回:
            Cell: 单元格对象
        """
        if cell_name in self.cells:
            logger.warning(f"单元格 {cell_name} 已存在")
            return self.cells[cell_name]
            
        try:
            kdb_cell = self.kdb_layout.create_cell(cell_name)
            self.cells[cell_name] = Cell(kdb_cell)
            logger.info(f"创建新单元格: {cell_name}")
            return self.cells[cell_name]
        except Exception as e:
            logger.error(f"创建单元格失败: {e}")
            return None

    def save(self, output_file, save_mapping=True):
        """保存 GDS 文件

        参数:
            output_file: 输出文件路径
            save_mapping: 是否保存图层映射
        """
        try:
            # 规范化输出路径
            output_file = os.path.abspath(os.path.normpath(output_file))

            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 使用简单的 write 方法,让 klayout 自动根据扩展名判断格式
            # 这种方式在打包和非打包环境下都能正常工作
            self.kdb_layout.write(output_file)
            logger.info(f"保存GDS文件: {output_file}")

            # 保存图层映射
            if save_mapping:
                basename, _ = os.path.splitext(output_file)
                for cell_name, cell in self.cells.items():
                    mapping_file = f"{basename}.{cell_name}.mapping"
                    cell.get_layer_manager().save_mapping(mapping_file)
        except Exception as e:
            logger.error(f"保存GDS文件失败: {e}") 