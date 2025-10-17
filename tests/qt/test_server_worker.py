import socket
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import werkzeug.serving  # noqa: F401
except ImportError:
    print("跳过 ServerWorker 测试：缺少 werkzeug 依赖")
    sys.exit(0)

from web_gui.server_worker import ServerWorker

from .stubs import simple_app


def _pick_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return port


def test_server_worker_serves_requests():
    port = _pick_free_port()
    worker = ServerWorker(simple_app, "127.0.0.1", port, debug=False)

    try:
        worker.start()
        assert worker.wait_ready(2.0), "server did not become ready in time"

        with urllib.request.urlopen(worker.url, timeout=2) as response:
            body = response.read().decode("utf-8")

        assert "stub response" in body
        assert worker.is_running()
    finally:
        worker.shutdown()
        assert not worker.is_running()
