from __future__ import annotations

import logging
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Callable

# Pre-warm matplotlib font cache and backends before anything else imports them.
# In a PyInstaller bundle the first import triggers a slow cache rebuild;
# doing it here avoids a confusing long pause.
def _seed_frozen_matplotlib_cache() -> None:
    if not getattr(sys, "frozen", False):
        return
    cache_root = Path(os.environ["MPLCONFIGDIR"])
    packaged_root = Path(getattr(sys, "_MEIPASS")) / "matplotlib-cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    for packaged_cache in packaged_root.glob("fontlist-v*.json"):
        destination = cache_root / packaged_cache.name
        if not destination.exists():
            shutil.copy2(packaged_cache, destination)


_seed_frozen_matplotlib_cache()
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager  # noqa: F401
import matplotlib.backends.backend_agg  # noqa: F401
import matplotlib.backends.backend_svg  # noqa: F401

from summer_gds.gui.qt_shell import run_qt_shell

# Fatal-error log file for --windowed mode (no console visible).
_CRASH_LOG = Path.home() / ".summer-gds-crash.log"
_DEBUG_LOG = Path.home() / ".summer-gds-debug.log"


def _log(message: str) -> None:
    """Append to debug log so we can trace startup even in --windowed mode."""
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(message + "\n")
    except OSError:
        pass


def main(shell_runner: Callable[[], int] = run_qt_shell) -> int:
    _log("=== Summer GDS starting === frozen=" + str(getattr(sys, "frozen", False)))
    try:
        exit_code = shell_runner()
    except Exception:
        _report_fatal(traceback.format_exc())
        return 1
    _log("=== Summer GDS exiting code=" + str(exit_code) + " ===")
    return exit_code


def _report_fatal(message: str) -> None:
    """Write crash log and attempt a GUI error dialog so --windowed isn't silent."""
    logging.critical("Summer GDS fatal error:\n%s", message)
    _log("FATAL: " + message)
    try:
        sep = "=" * 40
        _CRASH_LOG.write_text(
            "Summer GDS crash report\n" + sep + "\n" + message + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            "Summer GDS - Fatal Error",
            "Summer GDS failed to start.\n\nDetails saved to:\n" + str(_CRASH_LOG),
        )
        if QApplication.instance() is app:
            app.processEvents()
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
