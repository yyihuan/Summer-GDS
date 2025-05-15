import os
import sys
import yaml
from gds_utils.utils import setup_logging, logger

def test_main_script():
    """测试主脚本的执行"""
    # 设置日志
    setup_logging(True)
    logger.info("开始测试主脚本")
    
    # 创建测试配置
    config = {
        'global': {
            'dbu': 0.001,
            'fillet': {
                'interactive': False,
                'default_action': 'auto',
                'precision': 0.01
            },
            'layer_mapping': {
                'save': True,
                'file': 'script_test_mapping.txt'
            }
        },
        'gds': {
            'input_file': None,
            'output_file': 'script_test.gds',
            'cell_name': 'TEST',
            'default_layer': [1, 0]
        },
        'shapes': [
            {
                'type': 'polygon',
                'vertices': '0,0:100,0:100,100:0,100',
                'cell': 'TEST',
                'layer': [1, 0],
                'fillet_radius': 0
            },
            {
                'type': 'rings',
                'vertices': '200,0:300,0:300,100:200,100',
                'cell': 'TEST',
                'layer': [2, 0],
                'fillet_radius': 0,
                'ring_width': 10,
                'ring_space': 10,
                'ring_num': 3
            }
        ]
    }
    
    # 保存测试配置
    with open('script_test_config.yaml', 'w') as f:
        yaml.dump(config, f)
    
    # 调用主脚本
    try:
        logger.info("导入主脚本")
        from main_oop import main
        
        # 临时修改sys.argv以提供配置文件路径
        orig_argv = sys.argv
        sys.argv = ['main_oop.py', 'script_test_config.yaml']
        
        # 执行主脚本
        logger.info("执行主脚本")
        main()
        
        # 恢复sys.argv
        sys.argv = orig_argv
        
        # 检查输出文件是否创建
        if os.path.exists('script_test.gds'):
            logger.info("测试成功: GDS文件已创建")
            success = True
        else:
            logger.error("测试失败: GDS文件未创建")
            success = False
            
        # 清理测试文件
        if os.path.exists('script_test.gds'):
            os.remove('script_test.gds')
        if os.path.exists('script_test_config.yaml'):
            os.remove('script_test_config.yaml')
        for file in os.listdir('.'):
            if file.startswith('script_test') and file.endswith('.mapping'):
                os.remove(file)
                
        return success
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = test_main_script()
    print(f"测试结果: {'成功' if success else '失败'}")
    sys.exit(0 if success else 1) 