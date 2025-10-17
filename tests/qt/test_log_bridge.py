import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web_gui.log_bridge import LogBridge


def test_log_bridge_captures_warning():
    logger = logging.getLogger("gds_utils")
    original_level = logger.level

    bridge = LogBridge([logger])
    try:
        logger.warning("bridge warning %s", 1)
        events = bridge.drain()
    finally:
        logger.setLevel(original_level)
        bridge.close()

    assert events, "expected at least one log event"
    event = events[0]
    assert event.level_name == "WARNING"
    assert "bridge warning" in event.message
