import os
from .utils import logger

class LayerManager:
    """管理 Layer 的映射和索引"""
    
    def __init__(self):
        self.layer_mapping = {}  # (layer_num, datatype) -> layer_name
        self.layer_indices = {}  # (layer_num, datatype) -> layer_index
        self.next_index = 0  # 用于分配新的索引
        logger.debug("LayerManager 初始化")

    def get_layer_index(self, layer_info):
        """获取图层索引，不存在则返回None
        
        参数:
            layer_info: 图层信息元组 (layer_num, datatype)
            
        返回:
            int | None: 图层索引，不存在则返回None
        """
        return self.layer_indices.get(layer_info)

    def create_layer(self, layer_info, layer_name=None):
        """创建或获取图层索引
        
        参数:
            layer_info: 图层信息元组 (layer_num, datatype)
            layer_name: 图层名称，可选
            
        返回:
            int: 图层索引
        """
        # 检查图层是否已存在
        if layer_info in self.layer_indices:
            logger.warning(f"图层 {layer_info} 已存在，返回现有索引 {self.layer_indices[layer_info]}")
            # 更新图层名称（如果提供了新名称）
            if layer_name and layer_info in self.layer_mapping and self.layer_mapping[layer_info] != layer_name:
                logger.warning(f"更新图层名称: {self.layer_mapping[layer_info]} -> {layer_name}")
                self.layer_mapping[layer_info] = layer_name
            return self.layer_indices[layer_info]
        
        # 创建新图层索引
        layer_index = self.next_index
        self.next_index += 1
        self.layer_indices[layer_info] = layer_index
        
        # 设置图层名称（如果提供）
        if layer_name:
            self.layer_mapping[layer_info] = layer_name
            
        logger.debug(f"创建图层: {layer_info} -> 索引 {layer_index}, 名称 {layer_name}")
        return layer_index

    def get_layer_name(self, layer_info):
        """获取图层名称
        
        参数:
            layer_info: 图层信息元组 (layer_num, datatype)
            
        返回:
            str | None: 图层名称，不存在则返回None
        """
        return self.layer_mapping.get(layer_info)

    def get_all_layers(self):
        """获取所有图层信息
        
        返回:
            dict: {(layer_num, datatype): (index, name)}
        """
        return {k: (v, self.layer_mapping.get(k)) 
                for k, v in self.layer_indices.items()}

    def save_mapping(self, output_file):
        """保存图层映射到文件
        
        参数:
            output_file: 输出文件路径
        """
        if not self.layer_mapping:
            logger.warning(f"没有图层映射需要保存到 {output_file}")
            return
            
        try:
            with open(output_file, 'w') as f:
                f.write("# Layer Mapping\n")
                f.write("# Format: layer_num datatype index name\n")
                for layer_info, index in self.layer_indices.items():
                    layer_num, datatype = layer_info
                    name = self.layer_mapping.get(layer_info, "")
                    f.write(f"{layer_num} {datatype} {index} {name}\n")
            logger.info(f"图层映射已保存到 {output_file}")
        except Exception as e:
            logger.error(f"保存图层映射失败: {e}")

    def load_mapping(self, input_file):
        """从文件加载图层映射
        
        参数:
            input_file: 输入文件路径
        """
        if not os.path.exists(input_file):
            logger.error(f"映射文件不存在: {input_file}")
            return
            
        try:
            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        layer_num = int(parts[0])
                        datatype = int(parts[1])
                        index = int(parts[2])
                        name = parts[3] if len(parts) > 3 else None
                        
                        layer_info = (layer_num, datatype)
                        self.layer_indices[layer_info] = index
                        if name:
                            self.layer_mapping[layer_info] = name
                        
                        # 更新下一个可用索引
                        self.next_index = max(self.next_index, index + 1)
                        
            logger.info(f"已从 {input_file} 加载图层映射")
        except Exception as e:
            logger.error(f"加载图层映射失败: {e}") 