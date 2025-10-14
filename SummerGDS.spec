# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# 获取项目根目录
project_root = os.path.abspath(SPECPATH)

# 收集所有需要的数据文件
datas = [
    (os.path.join(project_root, 'web_gui', 'static'), 'web_gui/static'),
    (os.path.join(project_root, 'web_gui', 'templates'), 'web_gui/templates'),
    # 注意:不要把 gds_utils 作为数据文件打包,它会通过 import 自动打包
]

# 收集 klayout 的数据文件(如果有的话)
try:
    datas += collect_data_files('klayout')
except Exception:
    pass  # klayout 可能没有数据文件

# 收集所有隐藏导入
hiddenimports = [
    'klayout',
    'klayout.db',
    'klayout.lay',
    'yaml',
    'flask',
    'flask_cors',
    'werkzeug',
    'werkzeug.utils',
    'werkzeug.security',
    'numpy',
    'matplotlib',
    'ast',
    'tempfile',
    'json',
    'gds_utils',  # 确保 gds_utils 作为模块被打包
    'gds_utils.gds',
    'gds_utils.frame',
    'gds_utils.region',
    'gds_utils.cell',
    'gds_utils.layer',
    'gds_utils.utils',
]

# 添加 klayout 的所有子模块
hiddenimports += collect_submodules('klayout')

# 收集 klayout 的动态链接库
binaries = []
try:
    binaries += collect_dynamic_libs('klayout')
except Exception:
    pass  # 某些平台可能不需要额外的动态库

# 分析主程序
a = Analysis(
    [os.path.join(project_root, 'web_gui', 'run.py')],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 创建 PYZ 归档
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建可执行文件 (onedir 模式)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SummerGDS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 设为 True 可以看到日志输出,调试完成后可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 收集所有文件到一个目录中 (onedir)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SummerGDS',
)
