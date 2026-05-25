"""Summer-GDS Qt 启动器。

阶段 2 开始，该模块在原有参数解析能力的基础上，支持通过
`--headless` 选项直接启动 Flask 服务线程，同时捕获后端 `WARNING+`
日志，为后续 Qt 主窗口集成奠定基础。
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    from web_gui.log_bridge import LogEvent


@dataclass
class LaunchOptions:
    """Qt 入口所需的最终参数集合。"""

    host: str
    port: int
    debug: bool
    open_browser: bool
    headless: bool
    dry_run: bool
    headless_max_secs: Optional[float]
    wsgi_entry: Optional[str]
    config_path: Optional[Path]


DEFAULTS = LaunchOptions(
    host="0.0.0.0",
    port=5001,
    debug=False,
    open_browser=True,
    headless=False,
    dry_run=False,
    headless_max_secs=None,
    wsgi_entry=None,
    config_path=None,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summer-GDS Qt 启动器")
    parser.add_argument("--host", type=str, help="覆盖服务器监听地址")
    parser.add_argument("--port", type=int, help="覆盖服务器端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--config", type=str, help="web_gui JSON 配置文件路径")

    browser_group = parser.add_mutually_exclusive_group()
    browser_group.add_argument("--browser", action="store_true", help="强制打开嵌入式浏览器")
    browser_group.add_argument("--no-browser", action="store_true", help="禁止打开嵌入式浏览器")

    parser.add_argument("--dry-run", action="store_true", help="仅打印解析结果")
    parser.add_argument("--headless", action="store_true", help="仅启动后端服务（后续阶段实现）")
    parser.add_argument("--headless-exit-seconds", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--wsgi-entry", type=str, help=argparse.SUPPRESS)
    return parser


def _load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:  # pragma: no cover - 显式错误更友好
        raise ValueError(f"配置文件非合法 JSON: {config_path}\n{exc}")


def _merge_options(args: argparse.Namespace, config: Optional[Dict[str, Any]], config_path: Optional[Path]) -> LaunchOptions:
    options = LaunchOptions(
        host=args.host if args.host is not None else DEFAULTS.host,
        port=args.port if args.port is not None else DEFAULTS.port,
        debug=False,  # 暂时占位，随后合并
        open_browser=DEFAULTS.open_browser,
        headless=args.headless,
        dry_run=args.dry_run,
        headless_max_secs=args.headless_exit_seconds,
        wsgi_entry=args.wsgi_entry,
        config_path=config_path,
    )

    # 先应用配置文件，再应用命令行。
    if config:
        host = config.get("webgui_host")
        if host is not None and args.host is None:
            options.host = str(host)

        port = config.get("webgui_port")
        if port is not None and args.port is None:
            try:
                options.port = int(port)
            except (TypeError, ValueError):
                raise ValueError(f"配置项 webgui_port 非法: {port}")

        debug_flag = config.get("debug")
        if debug_flag is not None:
            options.debug = bool(debug_flag)

        auto_open = config.get("auto_open_browser")
        if auto_open is not None:
            options.open_browser = bool(auto_open)

    # 命令行覆盖配置。
    if args.debug:
        options.debug = True
    elif config is None:
        options.debug = DEFAULTS.debug
    else:
        # 如果配置文件没有 debug 字段，则沿用默认值。
        options.debug = options.debug if "debug" in config else DEFAULTS.debug

    if args.browser:
        options.open_browser = True
    if args.no_browser:
        options.open_browser = False

    return options


def _print_summary(options: LaunchOptions) -> None:
    print("Summer-GDS Qt Launcher")
    print(f"  Host          : {options.host}")
    print(f"  Port          : {options.port}")
    print(f"  Debug         : {options.debug}")
    print(f"  Open Browser  : {options.open_browser}")
    print(f"  Headless      : {options.headless}")
    print(f"  Dry Run       : {options.dry_run}")
    print(
        "  Headless Auto : "
        f"{options.headless_max_secs if options.headless_max_secs is not None else '(none)'}"
    )
    print(
        "  WSGI Entry    : "
        f"{options.wsgi_entry if options.wsgi_entry is not None else '(default)'}"
    )
    print(f"  Config Path   : {options.config_path if options.config_path else '(none)'}")


def _print_event(event: "LogEvent") -> None:
    prefix = f"[{event.level_name}] {event.logger_name}: {event.message}"
    print(prefix)
    if event.exc_text:
        print(event.exc_text)


def _load_wsgi_app(entry: Optional[str]):
    if entry is None:
        try:
            from web_gui.app import app as flask_app
        except ImportError as exc:
            raise RuntimeError("无法导入 web_gui.app，请确认环境配置正确") from exc
        return flask_app

    module_name, sep, attr = entry.partition(":")
    if not sep:
        raise RuntimeError("--wsgi-entry 需要形如 'module:object' 的格式")

    module = importlib.import_module(module_name)
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise RuntimeError(f"无法在模块 {module_name} 中找到 {attr}") from exc


def _run_headless(options: LaunchOptions) -> int:
    from web_gui.log_bridge import LogBridge
    from web_gui.server_worker import ServerWorker

    wsgi_app = _load_wsgi_app(options.wsgi_entry)

    if not callable(wsgi_app):
        raise RuntimeError("WSGI 入口必须是可调用对象")

    log_targets = [logging.getLogger(), logging.getLogger("gds_utils")]
    bridge = LogBridge(log_targets)
    server = ServerWorker(wsgi_app, options.host, options.port, debug=options.debug)

    try:
        server.start()
        if not server.wait_ready(timeout=5.0):
            print("服务器启动超时，5 秒内未就绪。")
            return 1

        print(f"Summer-GDS 服务已启动: {server.url}")
        if options.headless_max_secs:
            print(f"将在 {options.headless_max_secs}s 后自动退出。")
        else:
            print("按 Ctrl+C 停止服务器。")

        start_time = time.time()

        while True:
            if options.headless_max_secs and time.time() >= start_time + options.headless_max_secs:
                print("达到 headless 自动退出时间，准备关闭服务器。")
                break
            try:
                event = bridge.queue.get(timeout=0.5)
            except Empty:
                continue
            else:
                _print_event(event)

    except KeyboardInterrupt:
        print("\n检测到中断信号，正在关闭服务器...")
    finally:
        server.shutdown()
        for event in bridge.drain():
            _print_event(event)
        bridge.close()

    return 0


def _run_qt(options: LaunchOptions) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("缺少 PySide6 依赖，请先安装 PySide6。")
        return 1

    try:
        from web_gui.qt_mainwindow import MainWindow
    except ImportError as exc:
        print(f"无法导入 Qt 主窗口组件: {exc}")
        return 1

    from web_gui.log_bridge import LogBridge
    from web_gui.server_worker import ServerWorker

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    wsgi_app = _load_wsgi_app(options.wsgi_entry)
    if not callable(wsgi_app):
        MainWindow.show_startup_error("WSGI 入口必须是可调用对象")
        return 1

    log_targets = [logging.getLogger(), logging.getLogger("gds_utils")]
    bridge = LogBridge(log_targets)
    server = ServerWorker(wsgi_app, options.host, options.port, debug=options.debug)

    try:
        server.start()
        if not server.wait_ready(timeout=10.0):
            raise RuntimeError("服务在 10 秒内未就绪")
    except Exception as exc:  # noqa: BLE001 - 需要向用户暴露具体失败原因
        server.shutdown()
        bridge.close()
        MainWindow.show_startup_error(f"无法启动后端服务: {exc}")
        return 1

    window = MainWindow(server, bridge, options)
    window.show()

    try:
        return app.exec()
    finally:
        # 若窗口未触发 closeEvent（例如崩溃退出），确保资源回收。
        if server.is_running():
            server.shutdown()
        bridge.close()


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config: Optional[Dict[str, Any]] = None
    config_path: Optional[Path] = None
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
        try:
            config = _load_config(config_path)
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))

    options = _merge_options(args, config, config_path)

    if options.headless_max_secs is not None and options.headless_max_secs <= 0:
        parser.error("--headless-exit-seconds 需为正数")

    if options.wsgi_entry and not options.headless:
        parser.error("--wsgi-entry 仅能与 --headless 搭配使用")

    if options.dry_run:
        _print_summary(options)
        return 0

    if options.headless:
        return _run_headless(options)

    return _run_qt(options)


if __name__ == "__main__":
    sys.exit(main())
