from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, render_template, request

from summer_gds.gui.runtime import RequestGate
from summer_gds.gui.service import GuiSession, protocol_error


TOKEN_HEADER = "X-Summer-GDS-Token"


def create_app(
    *,
    session_token: str | None = None,
    temp_root: Path | None = None,
    gui_session: GuiSession | None = None,
    request_gate: RequestGate | None = None,
) -> Flask:
    token = session_token or secrets.token_urlsafe(32)
    session = gui_session or GuiSession(temp_root=temp_root)
    base_dir = Path(__file__).parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )
    app.config["SUMMER_GDS_SESSION_TOKEN"] = token
    app.config["SUMMER_GDS_GUI_SESSION"] = session
    app.config["SUMMER_GDS_REQUEST_GATE"] = request_gate
    app.config["DEBUG"] = False
    app.config["TESTING"] = False

    @app.before_request
    def require_session_token():
        g.summer_gds_gate_entered = False
        if not request.path.startswith("/api/"):
            return None
        if request.headers.get(TOKEN_HEADER) != token:
            return jsonify(protocol_error("forbidden", "$.headers", "Invalid GUI session token.")), 403
        if request_gate is not None:
            if not request_gate.try_enter():
                return jsonify(protocol_error("app_closing", "$", "The application is closing.")), 503
            g.summer_gds_gate_entered = True
        return None

    @app.teardown_request
    def leave_request_gate(_exception: BaseException | None) -> None:
        if getattr(g, "summer_gds_gate_entered", False):
            g.summer_gds_gate_entered = False
            assert request_gate is not None
            request_gate.leave()

    @app.get("/")
    def index():
        return render_template("index.html", session_token=token)

    @app.post("/api/parse")
    def parse_yaml():
        payload = _json_payload()
        if not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        yaml_text = payload.get("yaml_text")
        if not isinstance(yaml_text, str):
            return jsonify(protocol_error("invalid_request", "$.yaml_text", "yaml_text must be a string.")), 400
        return jsonify(session.parse(yaml_text))

    @app.post("/api/validate")
    def validate_yaml():
        payload = _json_payload()
        if not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        yaml_text = payload.get("yaml_text")
        if not isinstance(yaml_text, str):
            return jsonify(protocol_error("invalid_request", "$.yaml_text", "yaml_text must be a string.")), 400
        return jsonify(session.validate(yaml_text))

    @app.post("/api/preview/svg")
    def preview_svg():
        payload = _json_payload()
        if not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        yaml_text = payload.get("yaml_text")
        request_id = payload.get("request_id", "")
        if not isinstance(yaml_text, str):
            return jsonify(protocol_error("invalid_request", "$.yaml_text", "yaml_text must be a string.")), 400
        if not isinstance(request_id, str):
            return jsonify(protocol_error("invalid_request", "$.request_id", "request_id must be a string.")), 400
        return jsonify(session.preview_svg(yaml_text, request_id))

    @app.post("/api/file/choose-save")
    def choose_save_path():
        payload = _json_payload()
        if not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        kind = payload.get("kind")
        suggested_name = payload.get("suggested_name")
        if not isinstance(kind, str):
            return jsonify(protocol_error("invalid_request", "$.kind", "kind must be a string.")), 400
        if suggested_name is not None and not isinstance(suggested_name, str):
            return jsonify(protocol_error("invalid_request", "$.suggested_name", "suggested_name must be a string.")), 400
        return jsonify(session.choose_save_path(kind, suggested_name))

    @app.post("/api/yaml/open")
    def open_yaml():
        payload = _json_payload()
        if payload is not None and not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        return jsonify(session.open_yaml())

    @app.post("/api/yaml/save")
    def save_yaml():
        payload = _json_payload()
        if not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        yaml_text = payload.get("yaml_text")
        path_token = payload.get("path_token")
        force = payload.get("force", False)
        if not isinstance(yaml_text, str):
            return jsonify(protocol_error("invalid_request", "$.yaml_text", "yaml_text must be a string.")), 400
        if not isinstance(path_token, str):
            return jsonify(protocol_error("invalid_request", "$.path_token", "path_token must be a string.")), 400
        if not isinstance(force, bool):
            return jsonify(protocol_error("invalid_request", "$.force", "force must be a boolean.")), 400
        return jsonify(session.save_yaml(yaml_text, path_token, force))

    @app.post("/api/export/gds")
    def export_gds():
        payload = _json_payload()
        if not isinstance(payload, dict):
            return jsonify(protocol_error("invalid_request", "$", "Request body must be a JSON object.")), 400
        yaml_text = payload.get("yaml_text")
        path_token = payload.get("path_token")
        force = payload.get("force", False)
        if not isinstance(yaml_text, str):
            return jsonify(protocol_error("invalid_request", "$.yaml_text", "yaml_text must be a string.")), 400
        if not isinstance(path_token, str):
            return jsonify(protocol_error("invalid_request", "$.path_token", "path_token must be a string.")), 400
        if not isinstance(force, bool):
            return jsonify(protocol_error("invalid_request", "$.force", "force must be a boolean.")), 400
        return jsonify(session.export_gds(yaml_text, path_token, force))

    @app.teardown_appcontext
    def close_session(_exception: BaseException | None) -> None:
        if app.config.get("SUMMER_GDS_CLOSE_ON_TEARDOWN"):
            session.close()

    return app


def _json_payload() -> Any:
    return request.get_json(silent=True)
