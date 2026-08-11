# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Summer GDS v2 desktop GUI.

Usage (from project root):
    pyinstaller SummerGDS.spec
"""

import glob
import os
import sys
import klayout
import matplotlib
import matplotlib.font_manager  # Ensures the build-time cache exists.
from PyInstaller.utils.hooks import collect_data_files

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(SPECPATH)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
ICON_FILE = (
    os.path.join(PROJECT_ROOT, "packaging", "icons", "summergds-icon.ico")
    if sys.platform == "win32"
    else os.path.join(PROJECT_ROOT, "packaging", "icons", "summergds-icon.icns")
    if sys.platform == "darwin"
    else None
)

# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------
datas = []

# summer_gds GUI assets (templates + static)
gui_dir = os.path.join(SRC_DIR, "summer_gds", "gui")
datas.append((os.path.join(gui_dir, "templates"), "summer_gds/gui/templates"))
datas.append((os.path.join(gui_dir, "static"), "summer_gds/gui/static"))

# matplotlib data (fonts, backend configs)
try:
    datas += collect_data_files("matplotlib")
except Exception:
    pass
for font_cache in glob.glob(os.path.join(matplotlib.get_cachedir(), "fontlist-v*.json")):
    datas.append((font_cache, "matplotlib-cache"))

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
hiddenimports = [
    # klayout — pya is accessed via `import pya` but lives under klayout
    "klayout.db",
    "klayout.dbcore",
    "klayout.tl",
    "klayout.pya",
    "klayout.pyacore",
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

# ---------------------------------------------------------------------------
# Binaries: the GDS reader/writer plugin is loaded dynamically by KLayout.
# Native extension dependencies are otherwise discovered from the exact imports
# above by PyInstaller's binary analysis.
# ---------------------------------------------------------------------------
binaries = []
klayout_dir = os.path.dirname(klayout.__file__)
GDS_PLUGIN_PATTERNS = ("lib_gds2_dbpi.*", "_gds2_dbpi.*")
for plugin_pattern in GDS_PLUGIN_PATTERNS:
    for plugin in glob.glob(os.path.join(klayout_dir, "db_plugins", plugin_pattern)):
        if sys.platform == "win32":
            # The native db core discovers root/db_plugins, while the Python
            # package loader also probes klayout/db_plugins. Keep one source
            # binary and mirror it as data so PyInstaller does not deduplicate
            # the two required runtime locations.
            binaries.append((plugin, "db_plugins"))
            datas.append((plugin, "klayout/db_plugins"))
        else:
            binaries.append((plugin, "klayout/db_plugins"))

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
    console=False,
    icon=ICON_FILE,
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
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SummerGDS.app",
        icon=ICON_FILE,
        bundle_identifier="org.summergds.desktop",
    )
