#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


READY_TIMEOUT_SECONDS = 60
HARD_CEILING_SECONDS = 195
WINDOWS_DELETE_RETRY_ATTEMPTS = 60
WINDOWS_DELETE_RETRY_SECONDS = 1
TOKEN_RE = re.compile(r"window\.SUMMER_GDS_SESSION_TOKEN\s*=\s*(\"(?:[^\"\\]|\\.)*\")")
VALID_YAML = """schema_version: 2
global:
  unit: um
  dbu: 0.001
gds:
  top_cell: BUNDLE_PROBE
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
"""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dependency-inventory", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    project_root = args.project_root.resolve()
    dependency_inventory = _verify_inventory(bundle, project_root)
    if args.dependency_inventory is not None:
        inventory_path = args.dependency_inventory.resolve()
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(inventory_path, dependency_inventory)

    run_id = secrets.token_hex(32)
    probe_root = Path(tempfile.gettempdir()).resolve() / f"summer-gds-bundle-probe-{run_id}"
    probe_root.mkdir(mode=0o700)
    os.chmod(probe_root, 0o700)
    (probe_root / "session-root").mkdir(mode=0o700)
    _atomic_text(probe_root / "input.yaml", VALID_YAML)
    moved_parent = Path(tempfile.mkdtemp(prefix="Summer GDS 验证 🧪 "))
    moved_bundle = moved_parent / bundle.name
    shutil.copytree(bundle, moved_bundle, symlinks=True)
    executable = _executable(moved_bundle)
    env = _clean_environment()
    env["SUMMER_GDS_BUNDLE_PROBE_ROOT"] = str(probe_root)
    env["SUMMER_GDS_BUNDLE_PROBE_RUN_ID"] = run_id
    started = time.monotonic()
    process = subprocess.Popen([str(executable)], env=env)
    original_error: BaseException | None = None
    try:
        ready = _wait_json(probe_root / f"ready-{run_id}.json", READY_TIMEOUT_SECONDS)
        _validate_ready(ready, run_id, process.pid)
        _business_probe(ready["origin"], probe_root)
    except BaseException as exc:
        original_error = exc
    finally:
        _atomic_json(
            probe_root / f"command-{run_id}.json",
            {"schema_version": 1, "run_id": run_id, "command": "shutdown"},
        )
    remaining = max(0.1, HARD_CEILING_SECONDS - (time.monotonic() - started))
    try:
        exit_code = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise RuntimeError("bundle hard kill was required") from exc
    complete = _wait_json(probe_root / f"complete-{run_id}.json", 5)
    if original_error is not None:
        raise original_error
    if exit_code != 0 or complete.get("result") != "ok":
        raise RuntimeError(f"bundle cleanup failed: exit={exit_code}, complete={complete}")
    if complete.get("pid") != process.pid or complete.get("run_id") != run_id:
        raise RuntimeError("complete marker does not belong to this run")
    if not all(complete.get("cleanup", {}).values()):
        raise RuntimeError("bundle cleanup marker is incomplete")
    if any((probe_root / "session-root").iterdir()):
        raise RuntimeError("bundle session directory was not removed")
    _remove_tree(probe_root)
    _remove_tree(moved_parent)
    print(json.dumps({"ok": True, "bundle": str(bundle), "exit_code": exit_code}))
    return 0


def _remove_tree(path: Path) -> None:
    """Remove a verifier temporary tree, tolerating Windows' copied DLL attributes."""
    for attempt in range(WINDOWS_DELETE_RETRY_ATTEMPTS):
        try:
            shutil.rmtree(path, onexc=_clear_windows_readonly)
            return
        except PermissionError:
            if sys.platform != "win32" or attempt == WINDOWS_DELETE_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(WINDOWS_DELETE_RETRY_SECONDS)


def _clear_windows_readonly(func: object, path: str, exc_info: object) -> None:
    if sys.platform != "win32":
        raise exc_info[1]
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _verify_inventory(bundle: Path, project_root: Path) -> dict[str, object]:
    if sys.platform == "darwin":
        platform_plugin = "libqcocoa.dylib"
        webengine_helper = "QtWebEngineProcess"
    elif sys.platform == "win32":
        platform_plugin = "qwindows.dll"
        webengine_helper = "QtWebEngineProcess.exe"
    else:
        raise RuntimeError(f"unsupported bundle verifier platform: {sys.platform}")
    required = {
        "platform_plugin": list(bundle.rglob(platform_plugin)),
        "webengine_helper": list(bundle.rglob(webengine_helper)),
        "icu": list(bundle.rglob("icudtl.dat")),
        "resources": list(bundle.rglob("qtwebengine_resources.pak")),
        "locale_en": list(bundle.rglob("en-US.pak")),
        "locale_zh": list(bundle.rglob("zh-CN.pak")),
        "klayout_gds_plugin": list(bundle.rglob("*gds2_dbpi.*")),
    }
    missing = [name for name, paths in required.items() if not paths]
    if missing:
        raise RuntimeError(f"bundle inventory missing: {missing}")
    if sys.platform != "win32" and not os.access(required["webengine_helper"][0], os.X_OK):
        raise RuntimeError("QtWebEngine helper is not executable")
    _verify_klayout_plugin_locations(bundle, required["klayout_gds_plugin"])
    for relative in (
        "gui/templates/index.html",
        "gui/static/app.js",
        "gui/static/style.css",
        "gui/static/favicon.png",
    ):
        source = project_root / "src/summer_gds" / relative
        matches = list(bundle.rglob(f"summer_gds/{relative}"))
        if not matches or any(_sha256(source) != _sha256(match) for match in matches):
            raise RuntimeError(f"bundle static asset mismatch: {relative}")
    toc = (project_root / "build/SummerGDS/Analysis-00.toc").read_text(errors="replace")
    for forbidden in ("webview", "pythonnet", "clr_loader", "clr"):
        if re.search(rf"['\\\"]{re.escape(forbidden)}(?:\\.|['\\\"])", toc):
            raise RuntimeError(f"forbidden production module in TOC: {forbidden}")
    return _verify_dynamic_dependencies(bundle, project_root)


def _verify_klayout_plugin_locations(bundle: Path, plugins: list[Path]) -> None:
    if sys.platform != "win32":
        return
    payload_root = _runtime_payload_root(bundle)
    expected = {"db_plugins", "klayout/db_plugins"}
    matched = {}
    for path in plugins:
        try:
            relative = path.relative_to(payload_root)
        except ValueError:
            continue
        if relative.parent.as_posix() in expected:
            matched[relative.parent.as_posix()] = path
    missing = sorted(expected - set(matched))
    if missing:
        raise RuntimeError(f"bundle KLayout GDS plugin missing from: {missing}")
    hashes = {_sha256(path) for path in matched.values()}
    if len(hashes) != 1:
        raise RuntimeError("bundle KLayout GDS plugin copies differ")


def _runtime_payload_root(bundle: Path) -> Path:
    """Return the directory exposed to a frozen application as ``_MEIPASS``."""
    internal = bundle / "_internal"
    return internal if internal.is_dir() else bundle


def _verify_dynamic_dependencies(bundle: Path, project_root: Path) -> dict[str, object]:
    if sys.platform == "win32":
        return _verify_windows_dynamic_dependencies(bundle)
    if sys.platform != "darwin":
        raise RuntimeError(f"unsupported dynamic dependency platform: {sys.platform}")
    qt_entities: dict[str, set[Path]] = {}
    inventory: list[dict[str, str]] = []
    for binary in bundle.rglob("*"):
        if binary.is_symlink() or not binary.is_file() or binary.suffix == ".a":
            continue
        if (
            binary.suffix not in {".so", ".dylib"}
            and ".framework/Versions/" not in binary.as_posix()
            and binary.name not in {"SummerGDS", "QtWebEngineProcess"}
        ):
            continue
        identified = subprocess.run(
            ["file", "-b", str(binary)], capture_output=True, text=True
        ).stdout
        if "Mach-O" not in identified:
            continue
        output = subprocess.run(
            ["otool", "-L", str(binary)], capture_output=True, text=True
        ).stdout
        dependency_lines = "\n".join(output.splitlines()[1:])
        if str(project_root) in dependency_lines or "/.venv/" in dependency_lines:
            raise RuntimeError(f"build-machine dynamic dependency in {binary}")
        if "Qt" not in dependency_lines:
            continue
        for line in dependency_lines.splitlines():
            loader = line.strip().split(" (", 1)[0]
            match = re.search(r"(Qt(?:WebEngine)?[A-Za-z0-9]+)(?:\\.framework|\\.dylib)", loader)
            if not match:
                continue
            logical = match.group(1)
            candidates = list(bundle.rglob(f"{logical}.framework"))
            if candidates:
                resolved = candidates[0].resolve()
                qt_entities.setdefault(logical, set()).add(resolved)
                inventory.append(
                    {
                        "consumer": binary.relative_to(bundle).as_posix(),
                        "declared": loader,
                        "resolved": resolved.relative_to(bundle.resolve()).as_posix(),
                        "canonical": str(resolved),
                        "sha256": _sha256(resolved),
                    }
                )
    duplicates = {name: paths for name, paths in qt_entities.items() if len(paths) > 1}
    if duplicates:
        raise RuntimeError(f"multiple canonical Qt sources found: {duplicates}")
    return {"platform": "darwin", "qt_edges": inventory}


def _verify_windows_dynamic_dependencies(bundle: Path) -> dict[str, object]:
    binary_suffixes = {".dll", ".exe", ".pyd"}
    binaries = [
        path
        for path in bundle.rglob("*")
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in binary_suffixes
    ]
    by_name: dict[str, list[Path]] = {}
    for binary in binaries:
        by_name.setdefault(binary.name.casefold(), []).append(binary.resolve())

    required_qt = {
        "qt6core.dll",
        "qt6gui.dll",
        "qt6widgets.dll",
        "qt6network.dll",
        "qt6webenginecore.dll",
        "qt6webenginewidgets.dll",
    }
    for name in required_qt:
        matches = by_name.get(name, [])
        if not matches:
            raise RuntimeError(f"bundle Qt library is missing: {name}")
        if len(matches) != 1:
            raise RuntimeError(f"multiple canonical Qt sources found for {name}: {matches}")

    inventory: list[dict[str, str]] = []
    for binary in binaries:
        for declared in _pe_import_names(binary):
            normalized = declared.casefold()
            if not normalized.startswith("qt6") or not normalized.endswith(".dll"):
                continue
            matches = by_name.get(normalized, [])
            if not matches:
                raise RuntimeError(f"bundle binary imports Qt outside the bundle: {binary}: {declared}")
            if len(matches) != 1:
                raise RuntimeError(f"multiple canonical Qt sources found for {declared}: {matches}")
            resolved = matches[0]
            inventory.append(
                {
                    "consumer": binary.relative_to(bundle).as_posix(),
                    "declared": declared,
                    "resolved": resolved.relative_to(bundle.resolve()).as_posix(),
                    "canonical": str(resolved),
                    "sha256": _sha256(resolved),
                }
            )
    return {"platform": "win32", "qt_edges": inventory}


def _pe_import_names(path: Path) -> tuple[str, ...]:
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise RuntimeError(f"bundle binary is not PE: {path}")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\x00\x00":
        raise RuntimeError(f"bundle binary has invalid PE signature: {path}")
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic not in {0x10B, 0x20B}:
        raise RuntimeError(f"unsupported PE optional header: {path}")
    directory_offset = optional_offset + (112 if magic == 0x20B else 96)
    import_rva = struct.unpack_from("<I", data, directory_offset + 8)[0]
    if import_rva == 0:
        return ()
    section_offset = optional_offset + optional_size
    sections = []
    for index in range(section_count):
        offset = section_offset + 40 * index
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_offset))

    def offset_for(rva: int) -> int:
        for virtual_address, size, raw_offset in sections:
            if virtual_address <= rva < virtual_address + size:
                return raw_offset + rva - virtual_address
        raise RuntimeError(f"PE import RVA is outside sections: {path}: {rva:#x}")

    result = []
    offset = offset_for(import_rva)
    while True:
        original, _timestamp, _forwarder, name_rva, _first_thunk = struct.unpack_from("<IIIII", data, offset)
        if original == 0 and name_rva == 0:
            return tuple(result)
        name_offset = offset_for(name_rva)
        end = data.index(b"\x00", name_offset)
        result.append(data[name_offset:end].decode("ascii"))
        offset += 20


def _business_probe(origin: str, root: Path) -> None:
    opener = build_opener(ProxyHandler({}), NoRedirect())
    html = _request(opener, origin + "/", None, None)
    match = TOKEN_RE.search(html.decode())
    if not match:
        raise RuntimeError("session token bootstrap was not found")
    token = json.loads(match.group(1))
    headers = {"X-Summer-GDS-Token": token}
    opened = _json_request(opener, origin, "/api/yaml/open", {}, headers)
    yaml_text = opened["yaml_text"]
    parsed = _json_request(opener, origin, "/api/parse", {"yaml_text": yaml_text}, headers)
    assert parsed["ok"]
    assert _json_request(opener, origin, "/api/validate", {"yaml_text": yaml_text}, headers)["ok"]
    preview = _json_request(
        opener, origin, "/api/preview/svg", {"yaml_text": yaml_text, "request_id": "bundle-probe"}, headers
    )
    assert preview["ok"] and "<svg" in preview["svg_text"]
    yaml_choice = _json_request(
        opener, origin, "/api/file/choose-save", {"kind": "yaml", "suggested_name": None}, headers
    )
    gds_choice = _json_request(
        opener, origin, "/api/file/choose-save", {"kind": "gds", "suggested_name": None}, headers
    )
    assert _json_request(
        opener,
        origin,
        "/api/yaml/save",
        {"yaml_text": yaml_text, "path_token": yaml_choice["path_token"]},
        headers,
    )["ok"]
    assert _json_request(
        opener,
        origin,
        "/api/export/gds",
        {"yaml_text": yaml_text, "path_token": gds_choice["path_token"]},
        headers,
    )["ok"]
    assert (root / "output.yaml").read_text() == yaml_text
    assert (root / "output.gds").stat().st_size > 0
    import pya

    layout = pya.Layout()
    layout.read(str(root / "output.gds"))
    assert layout.cell("BUNDLE_PROBE") is not None


def _json_request(opener, origin, path, payload, headers):
    request_headers = {**headers, "Content-Type": "application/json"}
    data = _request(opener, origin + path, json.dumps(payload).encode("utf-8"), request_headers)
    result = json.loads(data)
    if not isinstance(result, dict):
        raise RuntimeError(f"invalid API response from {path}")
    return result


def _request(opener, url, data, headers):
    request = Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    try:
        with opener.open(request, timeout=20) as response:
            if response.geturl() != url:
                raise RuntimeError("redirected bundle origin")
            return response.read()
    except HTTPError as exc:
        raise RuntimeError(f"bundle API failed: {url}: {exc.code}") from exc


def _validate_ready(payload, run_id, pid):
    parsed = urlsplit(payload.get("origin", ""))
    if (
        payload.get("run_id") != run_id
        or payload.get("pid") != pid
        or payload.get("frozen") is not True
        or payload.get("dom_ready") is not True
        or parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port is None
        or parsed.username is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("invalid ready marker")


def _wait_json(path: Path, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            if path.stat().st_size > 16 * 1024:
                raise RuntimeError(f"oversized marker: {path}")
            return json.loads(path.read_text())
        time.sleep(0.05)
    raise TimeoutError(f"marker did not appear: {path}")


def _atomic_text(path: Path, text: str) -> None:
    temp = path.with_name("." + path.name + ".tmp")
    with open(temp, "x", encoding="utf-8") as stream:
        os.chmod(temp, stat.S_IRUSR | stat.S_IWUSR)
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def _atomic_json(path: Path, payload) -> None:
    _atomic_text(path, json.dumps(payload, sort_keys=True))


def _clean_environment():
    forbidden = (
        "PYTHONPATH",
        "PYTHONHOME",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "PYSIDE_DESIGNER_PLUGINS",
        "PYINSTALLER_CONFIG_DIR",
    )
    env = {key: value for key, value in os.environ.items() if key not in forbidden}
    if sys.platform != "win32":
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    return env


def _executable(bundle: Path) -> Path:
    if bundle.suffix == ".app":
        return bundle / "Contents/MacOS/SummerGDS"
    return bundle / ("SummerGDS.exe" if sys.platform == "win32" else "SummerGDS")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
