"""日志桥接工具。

该模块在阶段 2 中用于将 Python logging 的 WARNING+ 级别消息
转换为线程安全的事件队列，供 Qt 或 CLI 侧消费。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Iterable, List, Optional, Tuple


@dataclass
class LogEvent:
    level: int
    level_name: str
    logger_name: str
    message: str
    exc_text: Optional[str]


class QueueLogHandler(logging.Handler):
    """将日志消息写入 queue.Queue 的 handler。"""

    def __init__(self, queue: Queue):
        super().__init__(level=logging.WARNING)
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - 运行时验证
        try:
            msg = record.getMessage()
        except Exception:  # pragma: no cover - 避免日志异常导致崩溃
            msg = record.message if hasattr(record, "message") else "<failed to format message>"

        exc_text = None
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)

        event = LogEvent(
            level=record.levelno,
            level_name=record.levelname,
            logger_name=record.name,
            message=msg,
            exc_text=exc_text,
        )
        self._queue.put(event)


class LogBridge:
    """管理日志 handler 附着与消费。"""

    def __init__(self, targets: Iterable[logging.Logger]):
        self._queue: Queue = Queue()
        self._handler = QueueLogHandler(self._queue)
        self._targets: List[Tuple[logging.Logger, int]] = []
        self.attach(targets)

    @property
    def queue(self) -> Queue:
        return self._queue

    def attach(self, targets: Iterable[logging.Logger]) -> None:
        for target in targets:
            if self._handler not in target.handlers:
                target.addHandler(self._handler)
            original_level = target.level
            if target.level == logging.NOTSET or target.level > logging.WARNING:
                target.setLevel(logging.WARNING)
            self._targets.append((target, original_level))

    def detach(self) -> None:
        for target, original_level in self._targets:
            if self._handler in target.handlers:
                target.removeHandler(self._handler)
            target.setLevel(original_level)
        self._targets.clear()

    def drain(self) -> List[LogEvent]:
        items: List[LogEvent] = []
        while True:
            try:
                items.append(self._queue.get_nowait())
            except Empty:
                break
        return items

    def close(self) -> None:
        self.detach()
        self._handler.close()
