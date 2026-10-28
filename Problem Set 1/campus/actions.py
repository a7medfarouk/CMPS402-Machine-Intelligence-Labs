"""Shared actions for both the terminal menu and direct commands."""

import csv
import json
from pathlib import Path

from .feedback import LABELS, table
from .isolation import check_isolated, run_isolated
from .maps import MapSpec
from .public_checks import TITLES
from .terminal import display_path, notice, progress, say, show_table, verdict
from .viewer import write_viewer


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = [(name, "baseline") for name in ("bfs", "dfs", "ucs", "greedy", "astar")] + [("astar", "student")]
ALGORITHM_NAMES = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "greedy": "Greedy", "astar": "A*"}


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def detail(item):
    lines = [item.get("error", item.get("hint", "No diagnostic details."))]
    if item.get("location"):
        lines.append("Location: " + item["location"])
    if item.get("hint") and item["hint"] not in lines:
        lines.append("Next: " + item["hint"])
    return "\n".join(lines)


def check_summary(result, details=False):
    rows = [(str(item["number"]), item["check"], LABELS.get(item["status"], item["status"])) for item in result["checks"]]
    lines = [table(["#", "Public check", "Result"], rows), f"\nPassed {result['passed']}/{result['total']}. Public checks are not the final grade."]
    failures = [item for item in result["checks"] if not item.get("passed")]
    for item in failures if details else failures[:3]:
        lines.extend([f"\n[{item['number']}] {item['check']}", detail(item)])
    if len(failures) > 3 and not details:
        lines.append("\nMore failures: select Inspect saved failures, or app.py check --case NUMBER --details.")
    return "\n".join(lines)


def perform_checks(submission, indices=None, timeout=10, details=False, machine=False, previous=None):
    with progress(len(TITLES) if indices is None else len(indices), "Checking your code", enabled=not machine) as advance:
        result = check_isolated(submission, indices, timeout, on_result=lambda item: advance(item["check"]))
    if previous is not None and indices is not None:
        combined = {item["number"]: item for item in previous["checks"]}
        combined.update({item["number"]: item for item in result["checks"]})
        result["checks"] = [combined[number] for number in sorted(combined)]
        result.update(passed=sum(bool(item.get("passed")) for item in result["checks"]), total=len(combined))
    save_json(ROOT / "output/checks.json", result)
    (ROOT / "output/checks.txt").write_text(check_summary(result, True), encoding="utf-8")
    if machine:
        print(json.dumps(result, indent=2))
    else:
        show_table(["#", "Public check", "Result"], [(item["number"], item["check"], verdict(item["status"])) for item in result["checks"]], "Public checks")
        say(f"Passed {result['passed']}/{result['total']}. Public checks are not the final grade.")
        failures = [item for item in result["checks"] if not item.get("passed")]
        for item in failures if details else failures[:3]:
            notice(detail(item), f"Check {item['number']}: {item['check']}", "yellow")
        if len(failures) > 3 and not details:
            say("More failures: select Inspect saved failures, or app.py check --case NUMBER --details.", "dim")
        say("Full diagnostics: output/checks.txt", "dim")
    return result


def perform_run(submission, map_path, algorithm, heuristic, output, timeout=10, machine=False):
    specification = MapSpec.from_file(map_path)
    with progress(1, "Running your agent", enabled=not machine) as advance:
        record = run_isolated(specification, submission, algorithm, heuristic, timeout)
        advance()
    record["case"] = Path(map_path).stem
    save_json(output, record)
    write_viewer(record, Path(output).with_suffix(".html"))
    if machine:
        print(json.dumps(record, indent=2))
    else:
        show_table(["Result", "Cost", "Moves", "Expanded", "Seconds"], [[verdict(record["status"]), record["cost"] if record["cost"] is not None else "-", record["length"] if record["length"] is not None else "-", record["expansions"], f"{record['seconds']:.4f}"]], "Run summary")
        if record.get("error") or record.get("hint"):
            notice(detail(record), "Details", "yellow")
        notice(display_path(Path(output).with_suffix('.html')), "Replay saved")
        say("PASS means public/local checks passed, not a full certificate of your model's physics.", "dim")
    return record


def experiment_rows(records):
    return [{"Case": record["case"], "Family": record["family"].replace("_", " "), "Algorithm": ALGORITHM_NAMES[record["algorithm"]], "Heuristic": "My heuristic" if record["heuristic"] == "student" else ("Manhattan" if record["algorithm"] in {"astar", "greedy"} else "-"), "Result": LABELS.get(record["status"], record["status"]), "Cost": record["cost"] if record["cost"] is not None else "", "Moves": record["length"] if record["length"] is not None else "", "Expanded": record["expansions"], "Seconds": f"{record['seconds']:.4f}", "Message": record.get("error", record.get("hint", ""))} for record in records]


def perform_experiments(submission, output, timeout=10, quiet=False):
    suite = json.loads((ROOT / "maps/suite.json").read_text(encoding="utf-8"))
    records = []
    with progress(len(suite) * len(VARIANTS), "Comparing algorithms", enabled=not quiet) as advance:
        for case in suite:
            for algorithm, heuristic in VARIANTS:
                record = run_isolated(MapSpec(tuple(case["rows"])), submission, algorithm, heuristic, timeout)
                record.update(case=case["case"], family=case["family"])
                records.append(record)
                advance(f"{case['case']} / {ALGORITHM_NAMES[algorithm]}")
    output = Path(output)
    save_json(output / "experiments.json", records)
    rows = experiment_rows(records)
    with (output / "experiments.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    text = table(["Case", "Algorithm", "Heuristic", "Result", "Cost", "Moves", "Expanded", "Seconds"], [[row[key] for key in ("Case", "Algorithm", "Heuristic", "Result", "Cost", "Moves", "Expanded", "Seconds")] for row in rows])
    failures = [record for record in records if record["status"] != "ok"]
    for record in failures:
        text += "\n\n" + record["case"] + " / " + record["algorithm"] + " / " + record["heuristic"] + "\n" + detail(record)
    (output / "experiments.txt").write_text(text, encoding="utf-8")
    write_viewer(records, output / "experiments.html")
    totals = [(verdict(status), sum(record["status"] == status for record in records)) for status in dict.fromkeys(record["status"] for record in records)]
    show_table(["Result", "Runs"], totals, "Experiment summary")
    notice(f"Comparison: {display_path(output / 'experiments.html')}\nReadable table: {display_path(output / 'experiments.txt')}\nSpreadsheet: {display_path(output / 'experiments.csv')}", "Reports saved")
    say("These reports support your practice and live discussion. No written report or separate discussion files are required; upload Python files only.", "dim")
    return records
