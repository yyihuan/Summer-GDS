import unittest
import os
import yaml
from gds_utils import GDS, Frame, Region
from gds_utils.utils import setup_logging, logger

class TestGDSUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 设置测试日志
        cls.logger = setup_logging(show_log=False)
        
        # 创建测试配置
        cls.test_config = {
            'global': {
                'dbu': 0.001,
                'fillet': {
                    'interactive': False,
                    'default_action': 'auto',
                    'precision': 0.01
                },
                'layer_mapping': {
                    'save': True,
                    'file': 'test_layer_mapping.txt'
                }
            },
            'gds': {
                'input_file': None,
                'output_file': 'test_output.gds',
                'cell_name': 'TEST',
                'default_layer': [1, 0]
            },
            'shapes': [
                {
                    'type': 'polygon',
                    'vertices': '0,0:10,0:10,10:0,10',
                    'cell': 'TEST',
                    'layer': [1, 0],
                    'fillet_radius': 0
                },
                {
                    'type': 'rings',
                    'vertices': '0,0:10,0:10,10:0,10',
                    'cell': 'TEST',
                    'layer': [2, 0],
                    'fillet_radius': 0,
                    'ring_width': 2,
                    'ring_space': 2,
                    'ring_num': 2
                }
            ]
        }
        
        # 保存测试配置
        with open('test_config.yaml', 'w') as f:
            yaml.dump(cls.test_config, f)

    def setUp(self):
        # 每个测试前清理输出文件
        if os.path.exists('test_output.gds'):
            os.remove('test_output.gds')
        if os.path.exists('test_layer_mapping.txt'):
            os.remove('test_layer_mapping.txt')

    def test_frame_creation(self):
        """测试Frame创建和基本操作"""
        vertices = [(0, 0), (10, 0), (10, 10), (0, 10)]
        frame = Frame(vertices)
        
        # 测试顶点获取
        self.assertEqual(frame.get_vertices(), vertices)
        
        # 测试方向判断
        self.assertFalse(frame.is_clockwise())
        
        # 测试偏移
        offset_frame = frame.offset(2)
        self.assertIsInstance(offset_frame, Frame)
        self.assertEqual(len(offset_frame.get_vertices()), 4)

    def test_region_creation(self):
        """测试Region创建和布尔运算"""
        # 创建两个Frame
        frame1 = Frame([(0, 0), (10, 0), (10, 10), (0, 10)])
        frame2 = Frame([(5, 5), (15, 5), (15, 15), (5, 15)])
        
        # 创建Region
        region1 = Region.create_polygon(frame1)
        region2 = Region.create_polygon(frame2)
        
        # 测试布尔运算
        union_region = region1 + region2
        self.assertIsInstance(union_region, Region)
        
        diff_region = region1 - region2
        self.assertIsInstance(diff_region, Region)

    def test_gds_creation(self):
        """测试GDS文件创建和保存"""
        gds = GDS(
            input_file=None,
            cell_name='TEST',
            layer_info=(1, 0),
            dbu=0.001
        )
        
        # 测试cell创建
        cell = gds.create_cell('TEST2')
        self.assertIsNotNone(cell)
        
        # 测试重复创建
        cell2 = gds.create_cell('TEST2')
        self.assertEqual(cell, cell2)
        
        # 测试获取cells
        cells = gds.get_cells()
        self.assertEqual(len(cells), 2)  # TEST 和 TEST2

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 创建GDS对象
        gds = GDS(
            input_file=None,
            cell_name='TEST',
            layer_info=(1, 0),
            dbu=0.001
        )
        
        # 创建测试Frame
        frame = Frame([(0, 0), (10, 0), (10, 10), (0, 10)])
        
        # 创建Region
        region = Region.create_polygon(frame)
        
        # 获取cell并添加Region
        cell = gds.get_cell('TEST')
        cell.add_region(region, (1, 0))
        
        # 保存GDS文件
        gds.save('test_output.gds')
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists('test_output.gds'))

    def test_layer_mapping(self):
        """测试Layer映射功能"""
        gds = GDS(
            input_file=None,
            cell_name='TEST',
            layer_info=(1, 0),
            dbu=0.001
        )
        
        cell = gds.get_cell('TEST')
        layer_manager = cell.get_layer_manager()
        
        # 创建带名称的layer
        layer_index = layer_manager.create_layer((1, 0), 'metal1')
        self.assertIsNotNone(layer_index)
        
        # 测试获取layer名称
        layer_name = layer_manager.get_layer_name((1, 0))
        self.assertEqual(layer_name, 'metal1')
        
        # 测试保存mapping
        layer_manager.save_mapping('test_layer_mapping.txt')
        self.assertTrue(os.path.exists('test_layer_mapping.txt'))

if __name__ == '__main__':
    unittest.main() 