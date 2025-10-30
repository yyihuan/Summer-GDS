import json
from pathlib import Path
from typing import Any, Dict


_OUTPUT_ROOT = Path(__file__).resolve().parent / "_outputs"


def record_snapshot(suite: str, case: str, payload: Dict[str, Any]) -> None:
    """将测试输入/输出快照写入文件并打印，方便人工复核。"""

    suite_dir = _OUTPUT_ROOT / suite
    suite_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = suite_dir / f"{case}.json"
    with snapshot_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    # 同时打印到控制台，便于 pytest -s 直接查看
    print(f"[snapshot] {suite}/{case} -> {snapshot_path.relative_to(Path.cwd())}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
