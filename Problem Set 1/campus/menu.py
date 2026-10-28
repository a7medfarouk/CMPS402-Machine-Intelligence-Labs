"""Rich terminal app with arrow-key menus and optional direct commands."""

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import webbrowser

from .actions import ROOT, detail, perform_checks, perform_experiments, perform_run
from .feedback import LABELS
from .navigation import choose, configure
from .packaging import package_submission, read_identity, save_identity
from .public_checks import TITLES
from .terminal import ask, console, display_path, notice, pause, say, show_table
from .viewer import write_viewer


def open_if_requested(path):
    notice(display_path(path), "Saved file")
    if choose("Open the saved replay?", ["Open in browser", "Keep saved; return"]) == 0:
        webbrowser.open(Path(path).resolve().as_uri())


def show_failures():
    failures = []
    path = ROOT / "output/checks.json"
    if path.exists():
        for item in json.loads(path.read_text(encoding="utf-8"))["checks"]:
            if not item.get("passed"):
                failures.append((f"Check {item['number']}: {item['check']} [{LABELS.get(item['status'], item['status'])}]", item))
    path = ROOT / "output/experiments.json"
    if path.exists():
        for item in json.loads(path.read_text(encoding="utf-8")):
            if item["status"] != "ok":
                failures.append((f"{item['case']} / {item['algorithm']} / {item['heuristic']} [{LABELS.get(item['status'], item['status'])}]", item))
    if not failures:
        notice("No saved failures. Run public checks or experiments first.", "Saved failures")
        return
    while True:
        selected = choose("Inspect a saved failure", [label for label, item in failures])
        if selected is None:
            return False
        notice(detail(failures[selected][1]), failures[selected][0], "yellow")
        pause("Press Enter to return to the failure list.")


def edit_identity(submission):
    try:
        members = read_identity(submission)
        show_table(["Member", "ID"], [(member["name"], member["id"]) for member in members], "Current members")
    except (ValueError, FileNotFoundError):
        pass
    selected = choose("Team size", ["One member", "Two members"])
    if selected is None:
        return False
    members = []
    for index in range(selected + 1):
        members.append({"name": ask(f"Member {index + 1} full name: ").strip(), "id": ask(f"Member {index + 1} ID: ").strip()})
    if any(not member["name"] or not member["id"] for member in members):
        say("Names/IDs cannot be blank. No metadata was changed.", "yellow")
        return
    save_identity(submission, members)
    notice("Saved submission/student_info.py.", "Member details saved", "green")


def public_check_menu(submission):
    result = perform_checks(submission)
    while True:
        selected = choose("Public check results", ["Re-run all checks", "Re-run failed checks", "Re-run one check", "Read a check's details"])
        if selected is None:
            return
        if selected == 0:
            result = perform_checks(submission)
        elif selected == 1:
            indices = [item["number"] - 1 for item in result["checks"] if not item.get("passed")]
            if indices:
                result = perform_checks(submission, indices=indices, previous=result)
            else:
                notice("All saved checks passed. You can still re-run all or select one check.", "No failed checks", "green")
                pause("Press Enter for results options.")
        elif selected == 2:
            index = choose("Choose a check to re-run", TITLES)
            if index is not None:
                result = perform_checks(submission, indices=[index], details=True, previous=result)
        else:
            items = result["checks"]
            index = choose("Choose a check result", [str(item["number"]) + " · " + item["check"] + " · " + LABELS[item["status"]] for item in items])
            if index is not None:
                item = items[index]
                notice(detail(item) if not item.get("passed") else "This check passed. Public results are not the final grade.", item["check"])
                pause("Press Enter for results options.")


def optional_gym_menu(submission):
    notice("Optional and ungraded. Complete the required model/search first.\nEdit optional_gym/environment.py; these checks are separate from public checks.\nInstall once: uv sync --locked --extra gym", "Gymnasium extension")
    if importlib.util.find_spec("gymnasium") is None:
        say("Gymnasium is not installed. Run the installation command only if you want this extension.")
        pause()
        return
    if choose("Optional Gymnasium checks", ["Run optional adapter checks"]) == 0:
        subprocess.run([sys.executable, "-m", "optional_gym.checks", "--submission", str(Path(submission).resolve())], cwd=ROOT, check=False)
        pause()


def run_menu(submission):
    paths = sorted((ROOT / "maps").glob("*.txt"))
    labels = [path.stem.replace("_", " ") for path in paths]
    algorithms = ["bfs", "dfs", "ucs", "greedy", "astar"]
    while True:
        selected = choose("Choose a map", labels + ["Another text map (optional)"])
        if selected is None:
            return
        if selected < len(paths):
            map_path = paths[selected]
        else:
            map_path = Path(ask("Map path (blank goes back): ").strip().strip('"'))
            if str(map_path) == ".":
                continue
        while True:
            selected = choose("Choose an algorithm", ["BFS", "DFS", "UCS", "Greedy", "A*"])
            if selected is None:
                break
            algorithm, heuristic = algorithms[selected], "baseline"
            if algorithm in {"greedy", "astar"}:
                selected = choose("Choose a heuristic", ["Supplied Manhattan baseline", "My heuristic"])
                if selected is None:
                    continue
                heuristic = "student" if selected else "baseline"
            output = ROOT / "output/runs" / f"{map_path.stem}_{algorithm}_{heuristic}.json"
            perform_run(submission, map_path, algorithm, heuristic, output)
            open_if_requested(output.with_suffix(".html"))
            return


def main_menu(submission, setup, plain=False):
    configure(plain)
    while True:
        if console.is_terminal:
            console.clear()
        notice("Search assignment · 7 marks\nDeadline: Saturday 31/10/2026, 11:59 PM\nWork: submission/ | Reports: output/ | Guide: Instructions.html / .pdf", "CAMPUS COURIER")
        labels = ["Check setup", "Watch worked examples", "Run public checks", "Run my agent on a map", "Compare all algorithms", "Inspect saved failures", "Enter member names / IDs", "Build Python-only submission ZIP", "Assignment guide / commands", "Optional Gymnasium extension"]
        try:
            selected = choose("Main menu", labels, "Exit")
            if selected is None:
                say("Goodbye.", "dim")
                return 0
            if selected == 0:
                setup()
            elif selected == 1:
                path = ROOT / "output/demo.html"
                write_viewer(json.loads((ROOT / "examples/demo-runs.json").read_text(encoding="utf-8")), path)
                open_if_requested(path)
                continue
            elif selected == 2:
                public_check_menu(submission)
                continue
            elif selected == 3:
                run_menu(submission)
                continue
            elif selected == 4:
                perform_experiments(submission, ROOT / "output")
                open_if_requested(ROOT / "output/experiments.html")
                continue
            elif selected == 5:
                if show_failures() is False:
                    continue
            elif selected == 6:
                if edit_identity(submission) is False:
                    continue
            elif selected == 7:
                path = package_submission(submission, ROOT / "output/submissions")
                notice(f"Created: {display_path(path)}\nContents: Python files under submission/ only.\nNo written report or extra discussion files are required.", "ZIP ready", "green")
            elif selected == 8:
                notice("Start menu: uv run --locked app.py\nCheck code: uv run --locked app.py check\nSingle case: uv run --locked app.py check --case 7 --details\nComplete guide: Instructions.html or Instructions.pdf", "Assignment guide / commands")
                open_if_requested(ROOT / "Instructions.html")
                continue
            else:
                optional_gym_menu(submission)
                continue
            pause()
        except EOFError:
            say("Input closed. Goodbye.", "dim")
            return 0
        except KeyboardInterrupt:
            say("Cancelled. Returning to the menu.", "yellow")
        except Exception as error:
            notice(f"Could not complete that action: {error}\nSee Instructions.html; your source files were not removed.", "Action failed", "red")
            pause()
