"""Menu by default; the same actions are also available as direct commands."""

import argparse
import json
from pathlib import Path
import platform
import sys
from importlib.metadata import version

from .actions import ROOT, perform_checks, perform_experiments, perform_run
from .maps import MapSpec
from .packaging import package_submission
from .public_checks import TITLES
from .terminal import display_path, notice, say
from .viewer import write_viewer


def setup_check():
    if sys.version_info[:2] != (3, 14):
        raise ValueError("Use the locked Python 3.14 environment: run uv sync --locked, then uv run --locked app.py.")
    MapSpec(("SG",))
    for filename in ("examples/demo-runs.json", "maps/public-model-examples.json", "maps/public-facts.json"):
        if not json.loads((ROOT / filename).read_text(encoding="utf-8")):
            raise ValueError(f"Missing/empty supplied data: {filename}")
    notice(f"SETUP OK | Python {platform.python_version()} | Rich {version('rich')} | Questionary {version('questionary')}\nStarter functions may still be unfinished; setup does not run your algorithms.", "Environment ready", "green")


def selected_checks(value):
    if value is None:
        return None
    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(TITLES):
            return [index]
        raise ValueError(f"Check number must be between 1 and {len(TITLES)}.")
    indices = [index for index, title in enumerate(TITLES) if value.casefold() in title.casefold()]
    if not indices:
        raise ValueError("No matching checks. Use a check number, BFS, UCS, Model, or Heuristic.")
    return indices


def main():
    parser = argparse.ArgumentParser(description="Campus Courier: launch without a command for arrow-key menus. Start with Instructions.html or Instructions.pdf.")
    parser.add_argument("--submission", type=Path, default=ROOT / "submission", help="Implementation folder; normally leave unchanged")
    parser.add_argument("--plain-menu", action="store_true", help="Use numbered input if your terminal cannot handle arrow keys")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("menu", help="Launch the arrow-key terminal app")
    commands.add_parser("setup-check", help="Check Python and supplied files without running student code")
    checks = commands.add_parser("check", help="Readable public-check results")
    checks.add_argument("--case", help="A check number or part of its name")
    checks.add_argument("--details", action="store_true")
    checks.add_argument("--json", action="store_true", help="Optional machine-readable output")
    checks.add_argument("--timeout", type=float, default=10)
    demo = commands.add_parser("demo", help="Generate the worked-example viewer")
    demo.add_argument("--output", type=Path, default=ROOT / "output/demo.html")
    run = commands.add_parser("run", help="Run one map and save a diagnostic replay")
    run.add_argument("--map", type=Path, default=ROOT / "maps/demo.txt")
    run.add_argument("--algorithm", choices=["bfs", "dfs", "ucs", "greedy", "astar"], default="astar")
    run.add_argument("--heuristic", choices=["baseline", "student"], default="baseline")
    run.add_argument("--output", type=Path, default=ROOT / "output/run.json")
    run.add_argument("--timeout", type=float, default=10)
    run.add_argument("--json", action="store_true")
    experiments = commands.add_parser("experiments", help="Create the discussion comparison files")
    experiments.add_argument("--output", type=Path, default=ROOT / "output")
    experiments.add_argument("--timeout", type=float, default=10)
    experiments.add_argument("--quiet", action="store_true")
    view = commands.add_parser("view", help="Turn saved JSON into an offline replay")
    view.add_argument("input", type=Path)
    view.add_argument("--output", type=Path, default=ROOT / "output/replay.html")
    submit = commands.add_parser("submit", help="Package Python only with member names/IDs in the ZIP filename")
    submit.add_argument("--output", type=Path, default=ROOT / "output/submissions", help="Destination folder, not a custom ZIP filename")
    arguments = parser.parse_args()
    try:
        if arguments.command in {None, "menu"}:
            from .menu import main_menu
            return main_menu(arguments.submission, setup_check, arguments.plain_menu)
        if arguments.command == "setup-check":
            setup_check()
            return 0
        if arguments.command in {"demo", "view"}:
            source = ROOT / "examples/demo-runs.json" if arguments.command == "demo" else arguments.input
            write_viewer(json.loads(source.read_text(encoding="utf-8")), arguments.output)
            notice(f"Open this file in your browser: {display_path(arguments.output)}", "Replay saved")
            return 0
        if arguments.command == "submit":
            path = package_submission(arguments.submission, arguments.output)
            notice(f"ZIP READY: {display_path(path)}\nPython files only. No written report or additional discussion files are required.", "Submission ready", "green")
            return 0
        if arguments.timeout <= 0:
            raise ValueError("Time limit must be positive.")
        if arguments.command == "check":
            result = perform_checks(arguments.submission, selected_checks(arguments.case), arguments.timeout, arguments.details, arguments.json)
            return 0 if result["passed"] == result["total"] else 1
        if arguments.command == "run":
            record = perform_run(arguments.submission, arguments.map, arguments.algorithm, arguments.heuristic, arguments.output, arguments.timeout, arguments.json)
            return 0 if record["status"] in {"ok", "no_solution", "local_only"} else 1
        records = perform_experiments(arguments.submission, arguments.output, arguments.timeout, arguments.quiet)
        return 0 if all(record["status"] == "ok" for record in records) else 1
    except KeyboardInterrupt:
        say("Cancelled. Your source files are unchanged.", "yellow")
        return 130
    except Exception as error:
        notice(f"Could not complete the command: {error}\nHelp: Instructions.html or uv run --locked app.py --help", "Command failed", "red")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
