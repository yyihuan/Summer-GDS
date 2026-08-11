import os
import sys


assert "PySide6" not in sys.modules, "Qt unit tests must configure the platform before importing PySide6"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
