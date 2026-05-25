# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Summer GDS v2 desktop GUI.

Usage (from project root):
    # Step 1: verify with onedir (default)
    pyinstaller SummerGDS.spec

    # Step 2: switch to onefile for release — change MODE below
    # MODE = "onefile" then re-run
    pyinstaller SummerGDS.spec
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODE = "onedir"  # "onedir" for debug, "onefile" for release
PROJECT_ROOT = os.path.abspath(SPECPATH)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------
datas = []

# summer_gds GUI assets (templates + static)
gui_dir = os.path.join(SRC_DIR, "summer_gds", "gui")
datas.append((os.path.join(gui_dir, "templates"), "summer_gds/gui/templates"))
datas.append((os.path.join(gui_dir, "static"), "summer_gds/gui/static"))

# klayout data files
try:
    datas += collect_data_files("klayout")
except Exception:
    pass

# matplotlib data (fonts, backend configs)
try:
    datas += collect_data_files("matplotlib")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
hiddenimports = [
    # klayout — pya is accessed via `import pya` but lives under klayout
    "klayout",
    "klayout.db",
    "klayout.lay",
    "klayout.tl",
    "klayout.pya",
    "klayout.rdb",
    "klayout.lib",
    "klayout.pex",
    # web stack
    "flask",
    "werkzeug",
    "werkzeug.serving",
    "werkzeug.utils",
    "werkzeug.security",
    "jinja2",
    "markupsafe",
    # YAML
    "yaml",
    # image rendering — both Agg (PNG) and SVG backends
    "matplotlib",
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_svg",
    "PIL",
    # others
    "numpy",
]

try:
    hiddenimports += collect_submodules("klayout")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Binaries: klayout native libs (.so / .dylib / .dll)
# ---------------------------------------------------------------------------
binaries = []
try:
    binaries += collect_dynamic_libs("klayout")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [os.path.join(SRC_DIR, "summer_gds", "gui", "launcher.py")],
    pathex=[SRC_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
if MODE == "onefile":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="SummerGDS",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="SummerGDS",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,  # onedir keeps console for debugging
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="SummerGDS",
    )
