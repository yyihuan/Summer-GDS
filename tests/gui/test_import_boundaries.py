from __future__ import annotations

import subprocess
import sys


def test_gui_entry_reaches_qt_boundary_without_pywebview_modules():
    code = """
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'webview', 'pythonnet', 'clr_loader', 'clr'}:
        raise AssertionError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
from summer_gds.gui import launcher
assert launcher.main(lambda: 0) == 0
"""
    result = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_cli_import_does_not_load_qt():
    code = """
import sys
import summer_gds.cli
assert not any(name.startswith('PySide6') for name in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
