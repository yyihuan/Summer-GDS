# Summer-GDS Web GUI

这是一个用于Summer-GDS的Web图形界面，允许您通过浏览器创建和编辑GDS文件的配置。

## 功能特点

- 可视化编辑器，轻松创建多边形和环阵列
- 实时YAML预览
- JSON结构化编辑器
- 配置验证
- 一键生成GDS文件

## 安装

1. 确保已经安装了Summer-GDS的所有依赖：

```bash
pip install -r ../requirements.txt
```

2. 安装Web GUI所需的额外依赖：

```bash
pip install -r requirements.txt
```

## 启动服务器

1. 使用默认配置启动：

```bash
python run.py
```

默认将监听所有网络接口(0.0.0.0)，允许从任何IP访问。如果只希望在本地访问，可以使用：

```bash
python run.py --host=127.0.0.1
```

2. 或指定主机和端口：

```bash
python run.py --host=0.0.0.0 --port=8080
```

3. 在开发时启用调试模式：

```bash
python run.py --debug
```

启动后，打开浏览器访问 [http://localhost:5000](http://localhost:5000) (或您指定的其他地址和端口)。

## 使用方法

### 创建新配置

1. Web GUI启动时会加载一个默认的配置模板
2. 点击"添加形状"按钮可以添加多边形或环阵列
3. 填写各个形状的参数，如顶点坐标、图层信息、倒角设置等
4. 您可以通过"JSON编辑"标签页直接编辑配置的JSON结构
5. "YAML预览"标签页显示当前配置的YAML格式预览

### 保存和加载配置

- 点击"保存配置"按钮将当前配置保存为YAML文件
- 点击"加载配置"按钮可以从已有的YAML文件中加载配置

### 验证和生成

- 点击"验证配置"按钮会检查当前配置的有效性
- 点击"生成GDS"按钮会根据当前配置生成GDS文件并提供下载

## 配置文件格式

配置文件使用YAML格式，与Summer-GDS的命令行版本完全兼容。详细格式可参考主项目的README文档。

## 故障排除

如果在使用过程中遇到问题：

1. 确保所有依赖都已正确安装
2. 检查console日志中是否有错误信息
3. 尝试使用--debug选项启动服务以获取更多信息

## 联系与支持

如有任何问题，请参考Summer-GDS主项目的文档或提交Issue。 