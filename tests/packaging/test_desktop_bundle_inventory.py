from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = PROJECT_ROOT / "scripts" / "verify_desktop_bundle.py"
SPEC_PATH = PROJECT_ROOT / "SummerGDS.spec"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_desktop_bundle", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_inventory_fixture(root: Path, *, include_gds_plugin: bool) -> Path:
    bundle = root / "bundle"
    required_files = (
        "libqcocoa.dylib",
        "QtWebEngineProcess",
        "qwindows.dll",
        "QtWebEngineProcess.exe",
        "icudtl.dat",
        "qtwebengine_resources.pak",
        "en-US.pak",
        "zh-CN.pak",
    )
    for name in required_files:
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    os.chmod(bundle / "QtWebEngineProcess", 0o755)
    if include_gds_plugin:
        (bundle / "klayout" / "db_plugins").mkdir(parents=True)
        (bundle / "klayout" / "db_plugins" / "_gds2_dbpi.cp313-win_amd64.dll").write_bytes(b"fixture")
    for relative in (
        "gui/templates/index.html",
        "gui/static/app.js",
        "gui/static/style.css",
        "gui/static/favicon.png",
    ):
        source = root / "src/summer_gds" / relative
        bundled = bundle / "summer_gds" / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        bundled.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(relative.encode())
        bundled.write_bytes(relative.encode())
    toc = root / "build/SummerGDS/Analysis-00.toc"
    toc.parent.mkdir(parents=True)
    toc.write_text("[]", encoding="utf-8")
    return bundle


def test_bundle_inventory_requires_klayout_gds_plugin(tmp_path, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setattr(verifier, "_verify_dynamic_dependencies", lambda *_: None)

    with pytest.raises(RuntimeError, match="klayout_gds_plugin"):
        verifier._verify_inventory(_write_inventory_fixture(tmp_path, include_gds_plugin=False), tmp_path)


def test_bundle_inventory_accepts_windows_klayout_gds_plugin_name(tmp_path, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setattr(verifier, "_verify_dynamic_dependencies", lambda *_: None)
    monkeypatch.setattr(verifier.sys, "platform", "darwin")

    verifier._verify_inventory(_write_inventory_fixture(tmp_path, include_gds_plugin=True), tmp_path)


def test_windows_bundle_inventory_requires_matching_plugin_copies(tmp_path, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setattr(verifier, "_verify_dynamic_dependencies", lambda *_: None)
    monkeypatch.setattr(verifier.sys, "platform", "win32")
    bundle = _write_inventory_fixture(tmp_path, include_gds_plugin=True)

    with pytest.raises(RuntimeError, match="db_plugins"):
        verifier._verify_inventory(bundle, tmp_path)

    root_plugin = bundle / "db_plugins" / "_gds2_dbpi.cp313-win_amd64.dll"
    root_plugin.parent.mkdir()
    root_plugin.write_bytes((bundle / "klayout" / "db_plugins" / root_plugin.name).read_bytes())
    verifier._verify_inventory(bundle, tmp_path)


def test_windows_bundle_inventory_uses_pyinstaller_runtime_payload_root(tmp_path, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setattr(verifier, "_verify_dynamic_dependencies", lambda *_: None)
    monkeypatch.setattr(verifier.sys, "platform", "win32")
    bundle = _write_inventory_fixture(tmp_path, include_gds_plugin=True)
    source = bundle / "klayout" / "db_plugins" / "_gds2_dbpi.cp313-win_amd64.dll"
    payload = bundle / "_internal"
    copied = payload / "klayout" / "db_plugins" / source.name
    copied.parent.mkdir(parents=True)
    source.replace(copied)
    root_plugin = payload / "db_plugins" / source.name
    root_plugin.parent.mkdir()
    root_plugin.write_bytes(copied.read_bytes())

    verifier._verify_inventory(bundle, tmp_path)


def test_spec_uses_one_source_plugin_for_the_platform_specific_locations():
    spec = SPEC_PATH.read_text(encoding="utf-8")

    assert 'GDS_PLUGIN_PATTERNS = ("lib_gds2_dbpi.*", "_gds2_dbpi.*")' in spec
    assert 'binaries.append((plugin, "db_plugins"))' in spec
    assert 'datas.append((plugin, "klayout/db_plugins"))' in spec
    assert 'binaries.append((plugin, "klayout/db_plugins"))' in spec


def _write_windows_qt_fixture(bundle: Path) -> None:
    for name in (
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "Qt6Network.dll",
        "Qt6WebEngineCore.dll",
        "Qt6WebEngineWidgets.dll",
    ):
        (bundle / name).parent.mkdir(parents=True, exist_ok=True)
        (bundle / name).write_bytes(b"fixture")
    consumer = bundle / "klayout" / "_db.pyd"
    consumer.parent.mkdir(parents=True, exist_ok=True)
    consumer.write_bytes(b"fixture")


def test_windows_dynamic_dependencies_record_unique_qt_edges(tmp_path, monkeypatch):
    verifier = _load_verifier()
    bundle = tmp_path / "bundle"
    _write_windows_qt_fixture(bundle)

    def imports(binary: Path) -> tuple[str, ...]:
        return ("Qt6Core.dll", "Qt6Gui.dll") if binary.name == "_db.pyd" else ()

    monkeypatch.setattr(verifier, "_pe_import_names", imports)

    inventory = verifier._verify_windows_dynamic_dependencies(bundle)

    assert inventory["platform"] == "win32"
    assert inventory["qt_edges"] == [
        {
            "consumer": "klayout/_db.pyd",
            "declared": "Qt6Core.dll",
            "resolved": "Qt6Core.dll",
            "canonical": str((bundle / "Qt6Core.dll").resolve()),
            "sha256": verifier._sha256(bundle / "Qt6Core.dll"),
        },
        {
            "consumer": "klayout/_db.pyd",
            "declared": "Qt6Gui.dll",
            "resolved": "Qt6Gui.dll",
            "canonical": str((bundle / "Qt6Gui.dll").resolve()),
            "sha256": verifier._sha256(bundle / "Qt6Gui.dll"),
        },
    ]


def test_windows_dynamic_dependencies_reject_duplicate_qt_source(tmp_path):
    verifier = _load_verifier()
    bundle = tmp_path / "bundle"
    _write_windows_qt_fixture(bundle)
    duplicate = bundle / "nested" / "Qt6Core.dll"
    duplicate.parent.mkdir()
    duplicate.write_bytes(b"fixture")

    with pytest.raises(RuntimeError, match="multiple canonical Qt sources"):
        verifier._verify_windows_dynamic_dependencies(bundle)


def test_bundle_verifier_token_pattern_matches_the_bootstrap_assignment():
    verifier = _load_verifier()

    match = verifier.TOKEN_RE.search('window.SUMMER_GDS_SESSION_TOKEN = "token\\u002dvalue"')

    assert match is not None
    assert json.loads(match.group(1)) == "token-value"


def test_bundle_verifier_sends_json_content_type_for_api_requests():
    verifier = _load_verifier()

    class Response:
        def geturl(self):
            return "http://127.0.0.1:51700/api/parse"

        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    class Opener:
        request = None

        def open(self, request, timeout):
            self.request = request
            return Response()

    opener = Opener()
    response = verifier._json_request(
        opener,
        "http://127.0.0.1:51700",
        "/api/parse",
        {"yaml_text": "schema_version: 2"},
        {"X-Summer-GDS-Token": "test-token"},
    )

    assert response == {"ok": True}
    assert opener.request.get_header("Content-type") == "application/json"
    assert opener.request.get_header("X-summer-gds-token") == "test-token"


def test_windows_bundle_verifier_retries_transient_delete_lock(tmp_path, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setattr(verifier.sys, "platform", "win32")
    monkeypatch.setattr(verifier.time, "sleep", lambda _: None)
    calls = 0

    def remove_once_locked(_, *, onexc):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("sharing violation")

    monkeypatch.setattr(verifier.shutil, "rmtree", remove_once_locked)

    verifier._remove_tree(tmp_path / "moved-bundle")

    assert calls == 2


def test_windows_bundle_verifier_clears_readonly_before_delete_retry(tmp_path, monkeypatch):
    verifier = _load_verifier()
    monkeypatch.setattr(verifier.sys, "platform", "win32")
    chmod_calls = []
    removed = []

    monkeypatch.setattr(verifier.os, "chmod", lambda path, mode: chmod_calls.append((path, mode)))
    verifier._clear_windows_readonly(removed.append, "locked.pyd", (PermissionError, PermissionError(), None))

    assert chmod_calls == [("locked.pyd", verifier.stat.S_IWRITE)]
    assert removed == ["locked.pyd"]
