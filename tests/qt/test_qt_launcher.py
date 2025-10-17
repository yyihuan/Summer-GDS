import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = [sys.executable, "-m", "web_gui.qt_launcher"]


def run_launcher(args):
    completed = subprocess.run(
        LAUNCHER + args,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed


def parse_summary(stdout: str) -> Dict[str, str]:
    lines = {}
    for raw in stdout.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        lines[key.strip()] = value.strip()
    return lines


def test_default_options():
    result = run_launcher(["--dry-run"])
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    summary = parse_summary(result.stdout)
    assert summary["Host"] == "0.0.0.0"
    assert summary["Port"] == "5001"
    assert summary["Debug"] == "False"
    assert summary["Open Browser"] == "True"
    assert summary["Headless"] == "False"
    assert summary["Dry Run"] == "True"
    assert summary["Headless Auto"] == "(none)"
    assert summary["WSGI Entry"] == "(default)"
    assert summary["Config Path"] == "(none)"


def test_cli_overrides():
    result = run_launcher(
        [
            "--host=127.0.0.1",
            "--port=7000",
            "--debug",
            "--no-browser",
            "--dry-run",
        ]
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    summary = parse_summary(result.stdout)
    assert summary["Host"] == "127.0.0.1"
    assert summary["Port"] == "7000"
    assert summary["Debug"] == "True"
    assert summary["Open Browser"] == "False"


def test_config_file_merge():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "client_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "webgui_host": "192.168.9.9",
                    "webgui_port": 6100,
                    "debug": True,
                    "auto_open_browser": False,
                }
            ),
            encoding="utf-8",
        )

        result = run_launcher([f"--config={config_path}", "--dry-run"])
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        summary = parse_summary(result.stdout)
        assert summary["Host"] == "192.168.9.9"
        assert summary["Port"] == "6100"
        assert summary["Debug"] == "True"
        assert summary["Open Browser"] == "False"
        assert summary["Config Path"] == str(config_path.resolve())


def test_cli_precedence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "client_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "webgui_host": "10.0.0.5",
                    "webgui_port": 6100,
                    "debug": False,
                    "auto_open_browser": False,
                }
            ),
            encoding="utf-8",
        )

        result = run_launcher(
            [
                f"--config={config_path}",
                "--host=1.2.3.4",
                "--debug",
                "--browser",
                "--dry-run",
            ]
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
    summary = parse_summary(result.stdout)
    assert summary["Host"] == "1.2.3.4"
    assert summary["Debug"] == "True"
    assert summary["Open Browser"] == "True"


def test_missing_config_file():
    missing_path = PROJECT_ROOT / "non_exist_config.json"
    result = run_launcher([f"--config={missing_path}", "--dry-run"])
    if result.returncode == 0:
        raise AssertionError("预期失败，但命令返回 0")
    if "配置文件不存在" not in result.stderr:
        raise AssertionError(f"缺少预期的错误信息: {result.stderr}")


def test_headless_seconds_positive():
    result = run_launcher(["--headless", "--headless-exit-seconds=-1"])
    if result.returncode == 0:
        raise AssertionError("预期应当失败")
    if "需为正数" not in result.stderr:
        raise AssertionError(f"缺少预期提示: {result.stderr}")


def test_wsgi_entry_requires_headless():
    result = run_launcher(["--wsgi-entry=tests.qt.stubs:simple_app", "--dry-run"])
    if result.returncode == 0:
        raise AssertionError("预期失败，但命令返回 0")
    if "仅能与 --headless 搭配使用" not in result.stderr:
        raise AssertionError(f"缺少预期的错误信息: {result.stderr}")


def test_headless_with_stub():
    if importlib.util.find_spec("werkzeug") is None:
        print("跳过 Headless Stub 测试：缺少 werkzeug 依赖")
        return
    args = [
        "--headless",
        "--host=127.0.0.1",
        "--headless-exit-seconds=0.2",
        "--wsgi-entry=tests.qt.stubs:simple_app",
    ]
    result = run_launcher(args)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)


def main():
    tests = [
        (test_default_options, "默认解析"),
        (test_cli_overrides, "命令行覆盖"),
        (test_config_file_merge, "配置文件合并"),
        (test_cli_precedence, "命令行优先级"),
        (test_missing_config_file, "缺失配置文件"),
        (test_headless_seconds_positive, "Headless 秒数校验"),
        (test_wsgi_entry_requires_headless, "WSGI 参数依赖"),
        (test_headless_with_stub, "Headless Stub"),
    ]
    failures = []
    for func, name in tests:
        try:
            func()
        except AssertionError as exc:
            failures.append((name, str(exc)))
        except Exception as exc:  # pylint: disable=broad-except
            failures.append((name, f"未预期的异常: {exc}"))
    if failures:
        for name, detail in failures:
            print(f"[FAILED] {name}: {detail}")
        sys.exit(1)
    print("Qt 启动器参数解析测试通过")


if __name__ == "__main__":
    main()
