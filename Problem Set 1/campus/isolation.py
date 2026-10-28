"""Wall-clock limits for local runs, including imports and infinite loops."""

import json
import os
from pathlib import Path
import subprocess
import sys

from .runner import empty_record


ROOT = Path(__file__).resolve().parents[1]


def request_worker(request, timeout=10):
    if timeout <= 0:
        raise ValueError("Time limit must be positive")
    environment = {**os.environ, "PYTHONUTF8": "1"}
    try:
        process = subprocess.run([sys.executable, "-m", "campus.worker"], input=json.dumps(request), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=ROOT, env=environment)
    except subprocess.TimeoutExpired:
        return {"passed": False, "status": "time_limit", "error": f"Stopped after {timeout:g} seconds.", "hint": "Look for an infinite loop, missing duplicate detection, or an import that never finishes."}
    lines = [line for line in process.stdout.splitlines() if line.startswith("__CAMPUS_RESULT__")]
    if process.returncode or not lines:
        return {"passed": False, "status": "runtime_error", "error": (process.stderr or process.stdout or "Worker exited without a result.")[-2000:], "hint": "Check syntax/imports. Detailed output is saved in the report."}
    try:
        return json.loads(lines[-1].removeprefix("__CAMPUS_RESULT__"))
    except ValueError:
        return {"passed": False, "status": "runtime_error", "error": "The worker could not serialize its result.", "hint": "Use finite numeric costs and valid states."}


def run_isolated(specification, submission, algorithm, heuristic, timeout=10):
    request = {"task": "run", "submission": str(Path(submission).resolve()), "rows": specification.rows, "algorithm": algorithm, "heuristic": heuristic}
    result = request_worker(request, timeout)
    if "map" not in result:
        result = {**empty_record(specification, algorithm, heuristic), **result, "seconds": timeout if result["status"] == "time_limit" else 0}
    return result


def check_isolated(submission, indices=None, timeout=10, on_result=None):
    from .public_checks import TITLES
    indices = list(range(len(TITLES))) if indices is None else indices
    results = []
    for index in indices:
        result = request_worker({"task": "check", "submission": str(Path(submission).resolve()), "index": index}, timeout)
        results.append({**result, "number": index + 1, "check": TITLES[index]})
        if on_result is not None:
            on_result(results[-1])
    return {"passed": sum(bool(item.get("passed")) for item in results), "total": len(results), "checks": results, "scope": "Public diagnostics only; staff grading uses an independent private world and held-out cases."}
