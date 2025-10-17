import importlib.util
import os
import sys
from types import SimpleNamespace

if importlib.util.find_spec("PySide6") is None:
    print("跳过 Qt 主窗口测试：缺少 PySide6 依赖")
    sys.exit(0)

if importlib.util.find_spec("PySide6.QtWebEngineWidgets") is None:
    print("跳过 Qt 主窗口测试：缺少 QtWebEngine 依赖")
    sys.exit(0)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402  # pylint: disable=wrong-import-position

from web_gui.log_bridge import LogEvent  # noqa: E402  # pylint: disable=wrong-import-position
from web_gui.qt_mainwindow import MainWindow  # noqa: E402  # pylint: disable=wrong-import-position


class FakeBridge:
    def __init__(self):
        self._events = []

    def push(self, event: LogEvent) -> None:
        self._events.append(event)

    def drain(self):
        events, self._events = self._events, []
        return events

    def close(self):  # noqa: D401 - 简单实现
        self._events.clear()


class FakeServer:
    def __init__(self, url: str):
        self.url = url
        self.shutdown_called = False

    def shutdown(self):
        self.shutdown_called = True

    def is_running(self):
        return False


def main():
    app = QApplication.instance() or QApplication([])

    bridge = FakeBridge()
    server = FakeServer("http://127.0.0.1:5001")
    options = SimpleNamespace(open_browser=True)

    window = MainWindow(server, bridge, options)

    bridge.push(LogEvent(30, "WARNING", "test", "warning message", None))
    window._drain_logs()  # noqa: SLF001 - 测试内部逻辑

    content = window._log_view.toPlainText()  # noqa: SLF001 - 仅用于断言
    assert "warning message" in content

    window.close()
    app.processEvents()

    assert server.shutdown_called


if __name__ == "__main__":
    main()
