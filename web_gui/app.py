import os
import sys
import json
import yaml
import tempfile
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 添加父目录到路径，以便导入main_oop中的函数
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import main as gds_main

app = Flask(__name__)
CORS(app)  # 启用跨域请求

# 配置上传文件目录
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 配置临时文件目录
TEMP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)
app.config['TEMP_FOLDER'] = TEMP_FOLDER

# 默认配置模板
DEFAULT_CONFIG = {
    "global": {
        "dbu": 0.001,
        "fillet": {
            "interactive": False,
            "default_action": "auto",
            "precision": 0.01
        },
        "layer_mapping": {
            "save": True,
            "file": "layer_mapping.txt"
        }
    },
    "gds": {
        "input_file": None,
        "output_file": "output.gds",
        "cell_name": "TOP",
        "default_layer": [1, 0]
    },
    "shapes": []
}

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/default-config', methods=['GET'])
def get_default_config():
    """获取默认配置"""
    return jsonify(DEFAULT_CONFIG)

@app.route('/api/generate-gds', methods=['POST'])
def generate_gds():
    """根据配置生成GDS文件"""
    try:
        # 获取请求数据
        if request.content_type == 'application/json':
            config_data = request.json
        else:
            config_data = yaml.safe_load(request.form.get('config', '{}'))
        
        # 创建临时配置文件
        config_file = os.path.join(app.config['TEMP_FOLDER'], 'temp_config.yaml')
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # 设置输出文件路径
        output_file = os.path.join(app.config['TEMP_FOLDER'], config_data.get('gds', {}).get('output_file', 'output.gds'))
        config_data['gds']['output_file'] = output_file
        
        # 重写配置文件
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # 保存当前工作目录
        original_dir = os.getcwd()
        # 切换到包含main_oop.py的父目录
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 调用main_oop.py的main函数
        sys.argv = ['main_oop.py', config_file]
        gds_main()
        
        # 恢复工作目录
        os.chdir(original_dir)
        
        # 检查文件是否存在
        if not os.path.exists(output_file):
            return jsonify({"success": False, "error": "GDS文件生成失败"}), 500
            
        # 返回GDS文件供下载
        return send_file(output_file, as_attachment=True, download_name=os.path.basename(output_file))
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/validate-config', methods=['POST'])
def validate_config():
    """验证配置文件格式"""
    try:
        if request.content_type == 'application/json':
            config_data = request.json
        else:
            config_data = yaml.safe_load(request.form.get('config', '{}'))
        
        # 基本验证
        if not isinstance(config_data, dict):
            return jsonify({"valid": False, "errors": ["配置必须是一个有效的YAML对象"]}), 400
            
        if "global" not in config_data:
            return jsonify({"valid": False, "errors": ["缺少'global'配置部分"]}), 400
            
        if "gds" not in config_data:
            return jsonify({"valid": False, "errors": ["缺少'gds'配置部分"]}), 400
            
        if "shapes" not in config_data or not isinstance(config_data["shapes"], list):
            return jsonify({"valid": False, "errors": ["缺少'shapes'配置部分或者不是列表类型"]}), 400
            
        # 可以添加更多详细的验证规则
        
        return jsonify({"valid": True})
    except Exception as e:
        return jsonify({"valid": False, "errors": [str(e)]}), 400

@app.route('/api/save-config', methods=['POST'])
def save_config():
    """保存配置到文件"""
    try:
        config_data = request.json
        
        # 确保文件名安全
        filename = secure_filename(config_data.get('filename', 'config.yaml'))
        if not filename.endswith('.yaml'):
            filename += '.yaml'
            
        file_path = os.path.join(app.config['TEMP_FOLDER'], filename)
        
        # 提取并保存配置
        config_content = config_data.get('config', {})
        with open(file_path, 'w') as f:
            yaml.dump(config_content, f)
            
        return jsonify({"success": True, "file_path": file_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/load-config', methods=['POST'])
def load_config():
    """从文件加载配置"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "未找到文件"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "未选择文件"}), 400
        
    try:
        # 读取并解析YAML文件
        config_content = yaml.safe_load(file.stream)
        return jsonify({"success": True, "config": config_content})
    except Exception as e:
        return jsonify({"success": False, "error": f"配置文件解析错误: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000) 