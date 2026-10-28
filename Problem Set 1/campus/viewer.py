"""Generate a self-contained, map-first replay with no server or remote assets."""

import json
from pathlib import Path


ASSETS = Path(__file__).resolve().parent
TEMPLATE = (ASSETS / "replay.html").read_text(encoding="utf-8").replace("__STYLE__", (ASSETS / "replay.css").read_text(encoding="utf-8")).replace("__SCRIPT__", (ASSETS / "replay.js").read_text(encoding="utf-8"))


def write_viewer(records, path):
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        raise ValueError("Replay data must be a run or a list of runs.")
    for record in records:
        rows = record.get("map") if isinstance(record, dict) else None
        if not isinstance(rows, list) or not rows or any(not isinstance(row, str) or not row or len(row) != len(rows[0]) for row in rows):
            raise ValueError("A recorded run needs a nonempty rectangular map.")
    payload = json.dumps(records, allow_nan=False).replace("<", "\\u003c")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(TEMPLATE.replace("__PAYLOAD__", payload), encoding="utf-8")
