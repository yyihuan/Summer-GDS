"""Qt 主窗口定义。

阶段 3 负责将嵌入式浏览器与日志面板组合到统一窗口中，
并与后端服务共享生命周期。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QTextCursor
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView


def _resolve_state(name: str, fallback: int) -> int:
    try:
        return getattr(QWebEngineDownloadRequest, name)
    except AttributeError:
        state_enum = getattr(QWebEngineDownloadRequest, "DownloadState", None)
        if state_enum is not None:
            return getattr(state_enum, name, fallback)
        return fallback


DOWNLOAD_COMPLETED = _resolve_state("DownloadCompleted", 2)
DOWNLOAD_CANCELLED = _resolve_state("DownloadCancelled", 3)
DOWNLOAD_INTERRUPTED = _resolve_state("DownloadInterrupted", 4)

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    from web_gui.log_bridge import LogBridge, LogEvent
    from web_gui.qt_launcher import LaunchOptions
    from web_gui.server_worker import ServerWorker


class MainWindow(QMainWindow):
    """嵌入式 Web + 日志面板窗口。"""

    def __init__(
        self,
        server: "ServerWorker",
        bridge: "LogBridge",
        options: "LaunchOptions",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._server = server
        self._bridge = bridge
        self._options = options

        self.setWindowTitle("Summer-GDS")
        self.resize(1200, 800)

        self._splitter = QSplitter(Qt.Vertical, self)
        self._web_view = self._init_web_view()
        self._log_view = self._init_log_view()

        self._splitter.addWidget(self._web_view)
        self._splitter.addWidget(self._log_view)
        self._splitter.setStretchFactor(0, 4)
        self._splitter.setStretchFactor(1, 1)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)
        self.setCentralWidget(container)

        status_bar = QStatusBar(self)
        status_bar.showMessage(f"服务运行中: {self._server.url}")
        self.setStatusBar(status_bar)

        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._drain_logs)
        self._timer.start()

        QTimer.singleShot(0, self._apply_initial_split_ratio)

        self._setup_download_handler()

        if options.open_browser:
            self._web_view.setUrl(QUrl(self._server.url))
        else:
            # 若用户选择不展示浏览器，则提供简单提示。
            self._log_message("INFO", "launcher", "浏览器未加载 (--no-browser)")

    @staticmethod
    def show_startup_error(message: str) -> None:
        QMessageBox.critical(None, "Summer-GDS", message)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API 命名约定
        self._timer.stop()

        # 停止服务并刷新残留日志。
        try:
            self._server.shutdown()
        finally:
            for event_obj in self._bridge.drain():
                self._append_event(event_obj)
            self._bridge.close()

        super().closeEvent(event)

    def _init_web_view(self) -> QWebEngineView:
        view = QWebEngineView(self)
        view.setZoomFactor(1.0)
        view.setFocusPolicy(Qt.StrongFocus)
        return view

    def _init_log_view(self) -> QPlainTextEdit:
        widget = QPlainTextEdit(self)
        widget.setReadOnly(True)
        widget.setMaximumBlockCount(1000)
        widget.setPlaceholderText("等待服务日志...")
        widget.setMinimumHeight(160)
        return widget

    def _setup_download_handler(self) -> None:
        page = self._web_view.page()
        profile = page.profile()
        profile.downloadRequested.connect(self._handle_download)

    def _apply_initial_split_ratio(self) -> None:
        total = self._splitter.size().height()
        if total <= 0:
            total = max(self.height(), self._log_view.minimumHeight() * 5)

        top = max(1, int(total * 0.8))
        bottom = max(self._log_view.minimumHeight(), total - top)
        if bottom <= 0:
            bottom = self._log_view.minimumHeight()
            top = max(1, total - bottom)

        self._splitter.setSizes([top, bottom])

    def _handle_download(self, request) -> None:  # pragma: no cover - 需 Qt 运行环境
        target_dir = Path.cwd() / "downloads"
        target_dir.mkdir(parents=True, exist_ok=True)

        file_name = request.downloadFileName() or "download.gds"
        target_path = target_dir / file_name

        if target_path.exists():
            base = target_path.stem
            suffix = target_path.suffix
            counter = 1
            while True:
                candidate = target_dir / f"{base}_{counter}{suffix}"
                if not candidate.exists():
                    target_path = candidate
                    break
                counter += 1

        request.setDownloadDirectory(str(target_dir))
        request.setDownloadFileName(target_path.name)
        request.accept()

        self._log_message("INFO", "download", f"GDS 下载开始 -> {target_path}")

        def _on_finished(state):
            if state == DOWNLOAD_COMPLETED:
                self._log_message("INFO", "download", f"下载完成: {target_path}")
            elif state == DOWNLOAD_CANCELLED:
                self._log_message("WARNING", "download", "下载被取消")
            else:
                if state == DOWNLOAD_INTERRUPTED:
                    self._log_message("ERROR", "download", f"下载中断: {target_path}")
                else:
                    self._log_message("ERROR", "download", f"下载失败: {target_path}")
            request.stateChanged.disconnect(_on_finished)

        request.stateChanged.connect(_on_finished)

    def _drain_logs(self) -> None:
        for event in self._bridge.drain():
            self._append_event(event)

    def _append_event(self, event: "LogEvent") -> None:
        prefix = f"[{event.level_name}] {event.logger_name}: {event.message}"
        self._log_view.appendPlainText(prefix)
        if event.exc_text:
            self._log_view.appendPlainText(event.exc_text)
        cursor = self._log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._log_view.setTextCursor(cursor)

    def _log_message(self, level_name: str, logger_name: str, message: str) -> None:
        prefix = f"[{level_name}] {logger_name}: {message}"
        self._log_view.appendPlainText(prefix)
        cursor = self._log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._log_view.setTextCursor(cursor)
