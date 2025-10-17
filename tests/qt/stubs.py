"""测试阶段使用的 WSGI stub 应用。"""

from __future__ import annotations

import logging


def simple_app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    if path == "/warn":
        logging.getLogger("gds_utils").warning("模拟警告: %s", path)

    start_response("200 OK", [("Content-Type", "text/plain")])
    body = f"stub response for {path}".encode("utf-8")
    return [body]


simple_app.debug = False  # type: ignore[attr-defined]
