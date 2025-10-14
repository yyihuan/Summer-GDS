import os
import sys
import json
import yaml
import tempfile
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 判断是否在打包环境中运行
def get_base_path():
    """获取基础路径,兼容打包和开发环境"""
    if getattr(sys, 'frozen', False):
        # 打包后的环境:使用可执行文件所在目录
        return os.path.dirname(sys.executable)
    else:
        # 开发环境:使用脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """获取资源文件路径,兼容打包和开发环境"""
    if getattr(sys, 'frozen', False):
        # 打包后的环境:资源文件在 _MEIPASS 临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 添加父目录到路径，以便导入main_oop中的函数
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 如果是打包环境，还需要添加 _MEIPASS 路径
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)

from main import main as gds_main

# 配置 Flask 的模板和静态文件路径,兼容打包环境
if getattr(sys, 'frozen', False):
    # 打包环境:模板和静态文件在 _MEIPASS 中
    template_folder = os.path.join(sys._MEIPASS, 'web_gui', 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'web_gui', 'static')
else:
    # 开发环境:使用相对路径
    template_folder = 'templates'
    static_folder = 'static'

app = Flask(__name__,
            template_folder=template_folder,
            static_folder=static_folder)
CORS(app)  # 启用跨域请求

# 配置上传文件目录 - 使用用户可访问的目录,避免权限问题
BASE_PATH = get_base_path()
UPLOAD_FOLDER = os.path.join(BASE_PATH, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 配置临时文件目录 - 使用用户可访问的目录
TEMP_FOLDER = os.path.join(BASE_PATH, 'temp')
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

def ensure_string_values(config_data):
    """确保ring_width和ring_space保持为字符串类型"""
    if isinstance(config_data, dict):
        for key, value in config_data.items():
            if key in ['ring_width', 'ring_space']:
                config_data[key] = str(value)
            elif isinstance(value, (dict, list)):
                ensure_string_values(value)
    elif isinstance(config_data, list):
        for item in config_data:
            ensure_string_values(item)
    return config_data

def process_metadata(config_data):
    """处理配置元数据，确保后端兼容性"""
    if isinstance(config_data, dict):
        # 记录元数据用于调试，但不影响后端处理
        if '_metadata' in config_data:
            metadata = config_data['_metadata']
            print(f"Found shape metadata: source={metadata.get('source')}, "
                  f"generated_at={metadata.get('generated_at')}")

            # 元数据不参与实际的GDS生成，后端会忽略
            # 这里只是记录日志，不做任何处理

        # 递归处理嵌套结构
        for key, value in config_data.items():
            if isinstance(value, (dict, list)):
                process_metadata(value)

    elif isinstance(config_data, list):
        for item in config_data:
            process_metadata(item)

    return config_data

def ensure_metadata_compatibility(config_data):
    """确保元数据兼容性，为没有元数据的配置添加默认元数据"""
    if isinstance(config_data, dict) and 'shapes' in config_data:
        for shape in config_data['shapes']:
            if isinstance(shape, dict) and '_metadata' not in shape:
                # 为旧配置添加默认元数据
                shape['_metadata'] = {
                    'source': 'vertices',
                    'generated_at': '2024-10-14T00:00:00.000Z',  # 默认时间戳
                    'version': '1.0'
                }

    return config_data

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

        # 处理元数据
        config_data = process_metadata(config_data)

        # 确保ring_width和ring_space保持为字符串类型
        config_data = ensure_string_values(config_data)

        # 创建临时配置文件
        config_file = os.path.join(app.config['TEMP_FOLDER'], 'temp_config.yaml')
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_style='"')  # 使用双引号来确保字符串类型

        # 设置输出文件路径
        output_file = os.path.join(app.config['TEMP_FOLDER'], config_data.get('gds', {}).get('output_file', 'output.gds'))
        config_data['gds']['output_file'] = output_file

        # 重写配置文件
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_style='"')  # 使用双引号来确保字符串类型

        # 保存当前工作目录
        original_dir = os.getcwd()

        # 切换到包含main.py的父目录
        if getattr(sys, 'frozen', False):
            # 打包环境:需要切换到可执行文件的父目录
            work_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            work_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(work_dir)

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

        # 处理元数据
        config_data = process_metadata(config_data)

        # 确保ring_width和ring_space保持为字符串类型
        config_data = ensure_string_values(config_data)

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

        # 处理元数据
        config_data = process_metadata(config_data)

        # 确保ring_width和ring_space保持为字符串类型
        config_data = ensure_string_values(config_data)

        # 确保文件名安全
        filename = secure_filename(config_data.get('filename', 'config.yaml'))
        if not filename.endswith('.yaml'):
            filename += '.yaml'

        file_path = os.path.join(app.config['TEMP_FOLDER'], filename)

        # 提取并保存配置
        config_content = config_data.get('config', {})
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f,
                     default_style='"',  # 使用双引号来确保字符串类型
                     allow_unicode=True,
                     default_flow_style=False,
                     indent=2)

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

        # 确保元数据兼容性，为旧配置添加默认元数据
        config_content = ensure_metadata_compatibility(config_content)

        # 确保ring_width和ring_space保持为字符串类型
        config_content = ensure_string_values(config_content)

        return jsonify({"success": True, "config": config_content})
    except Exception as e:
        return jsonify({"success": False, "error": f"配置文件解析错误: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000) 