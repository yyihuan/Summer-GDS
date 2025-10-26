#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web GUI 后端验证 API 测试脚本
测试新增的全局精度控制验证功能
"""

import json
import requests
import time
import sys
from subprocess import Popen, PIPE

def test_web_gui_validation():
    """测试 Web GUI 后端验证 API"""

    # 启动 Flask 应用
    print("⏳ 启动 Web GUI 后端服务...")
    process = Popen(
        [sys.executable, "-m", "flask", "run"],
        cwd="web_gui",
        stdout=PIPE,
        stderr=PIPE,
        env={
            "FLASK_APP": "app.py",
            "FLASK_ENV": "development"
        }
    )

    # 等待服务启动
    time.sleep(3)

    try:
        base_url = "http://127.0.0.1:5000"

        # 测试 1: 获取默认配置
        print("\n[测试1] 获取默认配置...")
        response = requests.get(f"{base_url}/api/default-config")
        if response.status_code == 200:
            config = response.json()
            print("✓ 成功获取默认配置")
            print(f"  - dbu: {config['global']['dbu']}")
            print(f"  - precision: {config['global']['precision']}")
        else:
            print(f"✗ 失败: {response.status_code}")
            return False

        # 测试 2: 验证有效的精度配置 (dbu=0.001, precision=0.01)
        print("\n[测试2] 验证有效的精度配置 (dbu=0.001, precision=0.01)...")
        valid_config = {
            "global": {
                "dbu": 0.001,
                "precision": 0.01,
                "fillet": {"interactive": False}
            },
            "gds": {"output_file": "output.gds"},
            "shapes": []
        }
        response = requests.post(
            f"{base_url}/api/validate-config",
            json=valid_config
        )
        if response.status_code == 200 and response.json().get("valid"):
            print("✓ 验证通过")
        else:
            print(f"✗ 验证失败: {response.json()}")
            return False

        # 测试 3: 验证有效的高精度配置 (dbu=0.0001, precision=0.0001)
        print("\n[测试3] 验证有效的高精度配置 (dbu=0.0001, precision=0.0001)...")
        high_precision_config = {
            "global": {
                "dbu": 0.0001,
                "precision": 0.0001,
                "fillet": {"interactive": False}
            },
            "gds": {"output_file": "output.gds"},
            "shapes": []
        }
        response = requests.post(
            f"{base_url}/api/validate-config",
            json=high_precision_config
        )
        if response.status_code == 200 and response.json().get("valid"):
            print("✓ 验证通过")
        else:
            print(f"✗ 验证失败: {response.json()}")
            return False

        # 测试 4: 验证无精度控制配置 (precision=None)
        print("\n[测试4] 验证无精度控制配置 (precision=None)...")
        no_precision_config = {
            "global": {
                "dbu": 0.001,
                "precision": None,
                "fillet": {"interactive": False}
            },
            "gds": {"output_file": "output.gds"},
            "shapes": []
        }
        response = requests.post(
            f"{base_url}/api/validate-config",
            json=no_precision_config
        )
        if response.status_code == 200 and response.json().get("valid"):
            print("✓ 验证通过")
        else:
            print(f"✗ 验证失败: {response.json()}")
            return False

        # 测试 5: 验证无效配置 (precision/dbu 不是整数比)
        print("\n[测试5] 验证无效配置 (precision=0.0001, dbu=0.001)...")
        invalid_config = {
            "global": {
                "dbu": 0.001,
                "precision": 0.0001,
                "fillet": {"interactive": False}
            },
            "gds": {"output_file": "output.gds"},
            "shapes": []
        }
        response = requests.post(
            f"{base_url}/api/validate-config",
            json=invalid_config
        )
        if response.status_code == 400:
            error_data = response.json()
            if not error_data.get("valid"):
                print("✓ 正确识别为无效配置")
                print(f"  错误信息: {error_data['errors'][0]}")
            else:
                print(f"✗ 应该验证失败，但返回成功")
                return False
        else:
            print(f"✗ 预期错误，但返回: {response.status_code}")
            return False

        # 测试 6: 验证 dbu 超出范围
        print("\n[测试6] 验证 dbu 超出范围 (dbu=2.0)...")
        out_of_range_config = {
            "global": {
                "dbu": 2.0,
                "precision": None,
                "fillet": {"interactive": False}
            },
            "gds": {"output_file": "output.gds"},
            "shapes": []
        }
        response = requests.post(
            f"{base_url}/api/validate-config",
            json=out_of_range_config
        )
        if response.status_code == 400:
            error_data = response.json()
            if not error_data.get("valid"):
                print("✓ 正确识别为无效配置")
                print(f"  错误信息: {error_data['errors'][0]}")
            else:
                print(f"✗ 应该验证失败")
                return False
        else:
            print(f"✗ 预期错误，但返回: {response.status_code}")
            return False

        print("\n✅ 所有 Web GUI 后端验证测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False

    finally:
        # 终止 Flask 进程
        print("\n⏹️  停止 Web GUI 后端服务...")
        process.terminate()
        process.wait(timeout=5)

if __name__ == "__main__":
    success = test_web_gui_validation()
    sys.exit(0 if success else 1)
