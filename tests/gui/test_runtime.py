from __future__ import annotations

import threading
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from flask import Flask

from summer_gds.gui.runtime import RequestGate, start_loopback_server
from summer_gds.gui.server import create_app


def test_loopback_server_serves_gui_and_stops(tmp_path):
    app = create_app(session_token="test-token", temp_root=tmp_path)
    handle = start_loopback_server(app)
    handle.stop()
    handle.stop()

    assert handle.host == "127.0.0.1"
    assert handle.port > 0
    with pytest.raises(URLError):
        urlopen(handle.url, timeout=0.2)


def test_loopback_readiness_timeout_closes_server():
    app = Flask(__name__)

    @app.get("/")
    def wrong_page():
        return "not the application"

    with pytest.raises(TimeoutError):
        start_loopback_server(app, readiness_timeout=0.05)


def test_request_gate_rejects_new_entries_after_begin_shutdown():
    gate = RequestGate()
    assert gate.try_enter() is True
    gate.leave()
    gate.begin_shutdown()
    assert gate.try_enter() is False


def test_request_gate_waits_for_inflight_requests():
    gate = RequestGate()
    assert gate.try_enter()
    assert gate.wait_drained(0.01) is False
    gate.leave()
    assert gate.wait_drained(0.01) is True


def test_request_gate_leave_wakes_waiter():
    gate = RequestGate()
    assert gate.try_enter()
    result: list[bool] = []
    started = threading.Event()

    def wait_for_drain():
        started.set()
        result.append(gate.wait_drained(1.0))

    waiter = threading.Thread(target=wait_for_drain)
    waiter.start()
    assert started.wait(1)
    gate.leave()
    waiter.join(1)
    assert result == [True]


def test_request_gate_leave_underflow_is_failure():
    with pytest.raises(AssertionError):
        RequestGate().leave()
