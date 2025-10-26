"""
阶段一：后端参数识别测试

测试内容：
- YAML 参数解析
- precision/dbu 兼容性验证
- GDS 初始化时的参数设置
"""

import pytest
import yaml
import tempfile
import os
from gds_utils import GDS
from gds_utils.utils import validate_precision_dbu, set_global_dbu, get_global_dbu


class TestYamlParsing:
    """测试 YAML 参数解析"""

    def test_yaml_parsing_dbu_precision(self):
        """测试从 YAML 解析 dbu 和 precision"""
        config_yaml = """
global:
  dbu: 0.0001
  precision: 0.0001
gds:
  output_file: "output.gds"
shapes: []
"""
        config = yaml.safe_load(config_yaml)
        dbu = config['global']['dbu']
        precision = config['global']['precision']

        assert dbu == 0.0001
        assert precision == 0.0001

    def test_yaml_parsing_dbu_only(self):
        """测试仅指定 dbu，不指定 precision"""
        config_yaml = """
global:
  dbu: 0.001
gds:
  output_file: "output.gds"
shapes: []
"""
        config = yaml.safe_load(config_yaml)
        dbu = config['global']['dbu']
        precision = config['global'].get('precision')

        assert dbu == 0.001
        assert precision is None

    def test_yaml_parsing_default_dbu(self):
        """测试不指定 dbu 时使用默认值"""
        config_yaml = """
global:
  precision: 0.01
gds:
  output_file: "output.gds"
shapes: []
"""
        config = yaml.safe_load(config_yaml)
        dbu = config['global'].get('dbu', 0.001)
        precision = config['global'].get('precision')

        assert dbu == 0.001
        assert precision == 0.01


class TestPrecisionDbuValidation:
    """测试 precision 和 dbu 的兼容性验证"""

    def test_validate_precision_none(self):
        """测试 precision=None 时验证通过"""
        assert validate_precision_dbu(None, 0.001) is True
        assert validate_precision_dbu(None, 0.0001) is True

    def test_validate_precision_dbu_valid_cases(self):
        """测试有效的 precision/dbu 组合"""
        valid_cases = [
            (0.01, 0.001),    # 10
            (0.0001, 0.0001), # 1
            (0.001, 0.001),   # 1
            (0.1, 0.01),      # 10
            (0.1, 0.001),     # 100
            (0.0001, 0.00001), # 10
        ]

        for precision, dbu in valid_cases:
            assert validate_precision_dbu(precision, dbu) is True

    def test_validate_precision_dbu_invalid_ratio(self):
        """测试不兼容的 precision/dbu 组合（非整数比）"""
        invalid_cases = [
            (0.0001, 0.001),   # 0.1
            (0.00005, 0.001),  # 0.05
            (0.002, 0.001),    # 2 (实际上这个是有效的)
            (0.0003, 0.0001),  # 3 (实际上这个是有效的)
        ]

        # 重新列出真正无效的组合
        invalid_cases = [
            (0.0001, 0.001),   # 0.1 - 无效
            (0.00005, 0.001),  # 0.05 - 无效
        ]

        for precision, dbu in invalid_cases:
            with pytest.raises(ValueError):
                validate_precision_dbu(precision, dbu)

    def test_validate_dbu_out_of_range(self):
        """测试 dbu 超出范围"""
        with pytest.raises(ValueError):
            validate_precision_dbu(0.01, 2.0)  # dbu 太大

        with pytest.raises(ValueError):
            validate_precision_dbu(0.01, 0.000001)  # dbu 太小

    def test_validate_precision_out_of_range(self):
        """测试 precision 超出范围"""
        with pytest.raises(ValueError):
            validate_precision_dbu(2.0, 0.001)  # precision 太大

        with pytest.raises(ValueError):
            validate_precision_dbu(0.000001, 0.001)  # precision 太小


class TestGdsInitialization:
    """测试 GDS 初始化时的参数设置"""

    def test_gds_init_with_precision(self):
        """测试 GDS 初始化时正确存储 precision 和 dbu"""
        gds = GDS(
            cell_name="TOP",
            dbu=0.0001,
            precision=0.0001
        )

        assert gds.dbu == 0.0001
        assert gds.precision == 0.0001

    def test_gds_init_without_precision(self):
        """测试 GDS 初始化不指定 precision"""
        gds = GDS(
            cell_name="TOP",
            dbu=0.001,
            precision=None
        )

        assert gds.dbu == 0.001
        assert gds.precision is None

    def test_gds_init_default_values(self):
        """测试 GDS 初始化使用默认值"""
        gds = GDS()

        assert gds.dbu == 0.001
        assert gds.precision is None

    def test_gds_init_sets_global_dbu(self):
        """测试 GDS 初始化时设置全局 dbu"""
        # 先设置一个初始值
        set_global_dbu(0.001)
        assert get_global_dbu() == 0.001

        # 创建 GDS 对象，应该更新全局 dbu
        gds = GDS(dbu=0.0001)
        assert get_global_dbu() == 0.0001

        # 恢复默认值
        set_global_dbu(0.001)

    def test_gds_init_invalid_params_raises_error(self):
        """测试 GDS 初始化时无效的参数组合会抛出错误"""
        with pytest.raises(ValueError):
            GDS(dbu=0.001, precision=0.0001)

    def test_gds_kdb_layout_dbu_set(self):
        """测试 GDS 中 KLayout 的 dbu 被正确设置"""
        gds = GDS(dbu=0.0001)

        # KLayout 的 dbu 应该被设置
        assert gds.kdb_layout.dbu == 0.0001


class TestGlobalDbuManagement:
    """测试全局 dbu 管理"""

    def test_set_global_dbu(self):
        """测试设置全局 dbu"""
        set_global_dbu(0.0001)
        assert get_global_dbu() == 0.0001

        set_global_dbu(0.001)
        assert get_global_dbu() == 0.001

    def test_get_global_dbu_default(self):
        """测试获取全局 dbu 的默认值"""
        # 重置到默认值
        set_global_dbu(0.001)
        assert get_global_dbu() == 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
