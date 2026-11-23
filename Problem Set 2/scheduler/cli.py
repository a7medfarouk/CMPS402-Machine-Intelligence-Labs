"""Interactive and direct entry points for the assignment."""

import argparse
import json
from pathlib import Path
import sys
from importlib.metadata import version
import webbrowser

from .catalogue import Query, meeting, read_catalogue
from .checks import CHECKS
from .execution import LIMIT_SECONDS, ROOT, isolated
from .packaging import package, save_members
from .terminal import choose, notice, show_table, verdict


DATA = ROOT / "data/timetable.json"
SUBMISSION = ROOT / "submission"
WALKTHROUGH = ROOT / "examples/Walkthrough.html"
KINDS = ("schedule", "take", "avoid-day", "unavoidable")
ACTIONS = ("Find a schedule", "Can I take a section?", "Can I avoid a day?", "Is a section unavoidable?")
CASE_LABELS = {
    "alternatives": "Six-course timetable with alternatives",
    "single-course": "CMPS402: small unlinked example",
    "linked": "MTHS102: linked lecture and tutorial",
    "forced": "CMPS402 + MTHS102: one lecture left",
    "blocked": "CMPS402 + MTHS102: no valid timetable",
    "week": "Five-course practice timetable",
    "packed": "Six-course stress case",
    "empty": "No courses requested",
}
EXPLANATIONS = {
    "SCHEDULE FOUND": "A schedule was returned for the base request.",
    "POSSIBLE": "The shown schedule is a witness for this hypothetical restriction.",
    "IMPOSSIBLE": "The solver completed without a schedule under the hypothetical restriction.",
    "UNAVOIDABLE": "The base is feasible; excluding the named section left no solution.",
    "NOT UNAVOIDABLE": "The shown counterexample avoids the named section.",
    "BASE INFEASIBLE": "No solution was found for the base request; no necessity claim is made.",
    "INCONCLUSIVE": "The run reached a limit; no feasibility conclusion is made.",
}


def setup():
    if sys.version_info[:2] != (3, 14):
        raise ValueError("Use the project's locked Python 3.14 environment: uv sync --locked.")
    read_catalogue(DATA)
    if not (ROOT / "data/demo.json").is_file() or not WALKTHROUGH.is_file():
        raise ValueError("Worked example missing; extract the whole assignment ZIP.")
    notice(f"SETUP OK | Python {sys.version.split()[0]} | Rich {version('rich')} | Questionary {version('questionary')}",
           "Environment", "green")


def clock(minute):
    return f"{minute // 60:02}:{minute % 60:02}"


def case_label(name):
    return f"{name} - {CASE_LABELS[name]}" if name in CASE_LABELS else name


def show_schedule(catalogue, schedule):
    if not schedule:
        notice("No components are requested. The empty schedule is valid.", "Weekly timetable")
        return
    rows = []
    for component, identifier in schedule.items():
        section = next(section for section in catalogue.sections[component] if section.identifier == identifier)
        entry = section.meeting
        rows.append((catalogue.days.index(entry.day), entry.start, entry.end, component, identifier))
    show_table(("Day", "Time", "Component", "Section"),
               [(catalogue.days[day], clock(start) + "-" + clock(end), component, section)
                for day, start, end, component, section in sorted(rows)], "Weekly timetable")


def query_label(query):
    if query.kind == "avoid-day":
        return f"Can I avoid {query.day}?"
    if query.kind == "take":
        return f"Can I take {query.component} / {query.section}?"
    if query.kind == "unavoidable":
        return f"Is {query.component} / {query.section} unavoidable?"
    return "Find a schedule"


def show_result(catalogue, query, result, local=True):
    status = result["status"]
    notice(result.get("detail") or EXPLANATIONS.get(status, status),
           f"{query_label(query)} | {status}", verdict(status).style)
    if result.get("schedule") is not None:
        show_schedule(catalogue, result["schedule"])
    if result.get("runs"):
        show_table(("Solve", "Time (ms)", "Constraint calls", "Completion calls"),
                   [("Base" if index == 0 else f"What-if {index}", row["milliseconds"], row["constraint_checks"], row["completion_checks"])
                    for index, row in enumerate(result["runs"])], "Observed work")
    if local and status in EXPLANATIONS:
        notice("This is your code's answer, not a grading verdict. Use the public checks to verify it.", "Local result")


def job(folder, operation, case, query=None, blocks=(), timeout=LIMIT_SECONDS):
    arguments = ["-m", "scheduler.worker", str(folder), operation, case, "--timeout", str(timeout)]
    if query is not None:
        for option in ("kind", "component", "section", "day"):
            value = getattr(query, option)
            if value is not None:
                arguments.extend(["--" + option, value])
    for block in blocks:
        arguments.extend(["--block", block])
    return isolated(arguments, timeout=timeout)


def checks(folder, identifiers, previous=None):
    results = {} if previous is None else previous.copy()
    for identifier in identifiers:
        results[identifier] = job(folder, "check", identifier)
    show_table(("ID", "Public check", "Result", "Detail"),
               [(identifier, CHECKS[identifier][1], verdict(result["status"]), result.get("detail", ""))
                for identifier, result in results.items()], "Public checks")
    notice(f"Passed {sum(result['status'] == 'PASS' for result in results.values())}/{len(results)}.", "Summary")
    return results


def check_menu(folder, plain, identifiers=CHECKS):
    results = checks(folder, identifiers)
    while True:
        selection = choose("Public checks", ("Re-run all public checks", "Re-run failed checks shown above", "Run one check by name"), plain)
        if selection is None:
            return
        if selection == 0:
            results = checks(folder, CHECKS)
        elif selection == 1:
            failed = [key for key, result in results.items() if result["status"] != "PASS"]
            if failed:
                results = checks(folder, failed, results)
            else:
                notice("No failed checks to re-run.")
        else:
            names = tuple(CHECKS)
            chosen = choose("Check", tuple(CHECKS[name][1] for name in names), plain)
            if chosen is not None:
                results = checks(folder, [names[chosen]], results)


def demo(catalogue):
    example = json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8"))
    for item in example["queries"]:
        query = Query(**item["query"])
        notice(item["reason"], f"{item['title']} | {item['case']}")
        for index, restriction in enumerate(item["restrictions"]):
            if index == 0:
                notice("solve_request({}) - unchanged request", "1. Base solve")
            else:
                kept = "; ".join(f"{component}: {', '.join(values) or 'no choices'}" for component, values in restriction.items())
                notice(kept or "No extra restriction.", f"{index + 1}. What-if solve: keep only these choices")
        show_result(catalogue, query, item["result"], local=False)
    for comparison in example["comparisons"]:
        title = f"{case_label(comparison['case'])} ({len(comparison['components'])} components)"
        show_table(("Method", "Constraint checks", "Completion checks"),
                   [(row["name"], row["constraint_checks"], row["completion_checks"])
                    for row in comparison["rows"]], title)
        notice(f"Both: {comparison['result']}. {comparison['note']}", "How to read this comparison")
    notice("A constraint check calls a yes/no rule; a completion check asks whether all components are assigned.",
           "What the counters mean")
    notice(f"Open {WALKTHROUGH} for the weekly grids and side-by-side solver comparison.", "Offline walkthrough")


def open_guide(path):
    if not webbrowser.open(path.resolve().as_uri()):
        notice(f"Open this file in a browser: {path}", "Browser did not open")


def show_request(catalogue, request, blocks=()):
    rows = []
    for component in request.components:
        for section in catalogue.sections[component]:
            entry = section.meeting
            times = f"{entry.day} {clock(entry.start)}-{clock(entry.end)}"
            rows.append((component, section.identifier, times))
    courses = dict.fromkeys(component.partition(".")[0] for component in request.components)
    notice("\n".join(f"{course} - {catalogue.course_names.get(course, course)}" for course in courses) or "No courses.", "Requested courses")
    show_table(("Component", "Section", "Weekly slot"), rows, "Catalogue choices")
    links = [(link.components[0], link.components[1], ", ".join(f"{first} + {second}" for first, second in sorted(link.allowed)) or "No allowed pairs")
             for link in catalogue.links if set(link.components) <= set(request.components)]
    if links:
        show_table(("First component", "Second component", "Allowed pairs"), links, "Section links")
    notice("Only listed links restrict pairings. Unlinked sections can be mixed if their slots do not clash or hit a blocked time.",
           "Pairing rules" if links else "No links for this request")
    intervals = [f"{entry.day} {clock(entry.start)}-{clock(entry.end)}" for entry in request.unavailable]
    notice("; ".join([*intervals, *blocks]) or "None", "Unavailable times")


def select_query(catalogue, request, plain):
    selected = choose("Advisor question", ACTIONS, plain)
    if selected is None:
        return None
    kind = KINDS[selected]
    if kind == "schedule":
        return Query(kind)
    if kind == "avoid-day":
        day = choose("Day to avoid", catalogue.days, plain)
        return Query(kind, day=catalogue.days[day]) if day is not None else None
    components = tuple(component for component in request.components if catalogue.sections[component])
    if not components:
        notice("This request has no sections to query.")
        return None
    selected = choose("Component", components, plain)
    if selected is None:
        return None
    component = components[selected]
    sections = catalogue.sections[component]
    labels = tuple(f"{section.identifier} · {section.meeting.day} {clock(section.meeting.start)}-{clock(section.meeting.end)}"
                   for section in sections)
    selected = choose("Section", labels, plain)
    return Query(kind, component, sections[selected].identifier) if selected is not None else None


def menu(folder, catalogue, requests, plain):
    names, current, blocks = tuple(requests), "alternatives", []
    while True:
        try:
            selected = choose("Scheduling Advisor", (
                "Start here - setup, instructions and worked examples",
                "Implement and test - public checks by file",
                f"Try your advisor - {case_label(current)}",
                "Submit - member details or ZIP",
            ), plain, "Exit")
            if selected is None:
                return 0
            if selected == 0:
                action = choose("Start here", ("Open the offline walkthrough", "Read examples in this terminal",
                                              "Open instructions", "Check setup"), plain)
                if action in (0, 2):
                    open_guide(WALKTHROUGH if action == 0 else ROOT / "Instructions.html")
                    continue
                if action == 1:
                    demo(catalogue)
                elif action == 3:
                    setup()
                else:
                    continue
            elif selected == 1:
                stage = choose("Choose what you have implemented", ("All checks", "model.py - timetable model",
                               "solver.py - generic CSP solver", "advisor.py - what-if queries",
                               "model.py - AC-3 checks"), plain)
                if stage is not None:
                    if stage == 4:
                        identifiers = [name for name in CHECKS if name.startswith("ac3-")]
                    else:
                        part = ("all", "model", "solver", "advisor")[stage]
                        identifiers = [name for name, spec in CHECKS.items() if stage == 0 or spec[0] == part]
                    check_menu(folder, plain, identifiers)
                continue
            elif selected == 2:
                while True:
                    action = choose(f"{case_label(current)} | {len(blocks)} extra blocked slots",
                                    ("Ask a question using my code", "View sections, links and blocked times",
                                     "Choose a different request", "Add an unavailable time", "Clear extra blocked times",
                                     "See the worked timetable (no code needed)"), plain)
                    if action is None:
                        break
                    if action == 0:
                        query = select_query(catalogue, requests[current], plain)
                        if query is not None:
                            show_result(catalogue, query, job(folder, "run", current, query, blocks))
                            input("Press Enter for the request menu.")
                    elif action == 1:
                        show_request(catalogue, requests[current], blocks)
                        input("Press Enter for the request menu.")
                    elif action == 2:
                        case = choose("Request", tuple(map(case_label, names)), plain)
                        if case is not None and names[case] != current:
                            current, blocks = names[case], []
                    elif action == 3:
                        day = choose("Day", catalogue.days, plain)
                        if day is not None:
                            block = ",".join((catalogue.days[day], input("Start (HH:MM): ").strip(), input("End (HH:MM): ").strip()))
                            meeting(block.split(","), catalogue.days)
                            blocks.append(block)
                    elif action == 4:
                        blocks.clear()
                    else:
                        open_guide(WALKTHROUGH)
                continue
            else:
                action = choose("Submission", ("Enter member details", "Build the Python-only ZIP"), plain)
                if action == 0:
                    size = choose("Team size", ("One member", "Two members"), plain)
                    if size is None:
                        continue
                    members = [{"name": input(f"Member {index} full name: ").strip(),
                                "id": input(f"Member {index} ID: ").strip()}
                               for index in range(1, size + 2)]
                    save_members(folder, members)
                    notice("Member details saved.")
                elif action == 1:
                    notice(str(package(folder, ROOT / "output/submissions")), "Submission ZIP")
                else:
                    continue
            input("Press Enter to return.")
        except (ValueError, OSError, SyntaxError) as error:
            notice(error, "Could not complete action", "yellow")
            try:
                input("Press Enter to return.")
            except EOFError:
                return 0
        except KeyboardInterrupt:
            notice("Action cancelled.")
        except EOFError:
            return 0


def main():
    parser = argparse.ArgumentParser(description="Scheduling Advisor. Launch without a command for the menu.")
    parser.add_argument("--plain-menu", action="store_true")
    parser.add_argument("--submission", type=Path, default=SUBMISSION, help="Directory of the implementation to run")
    commands = parser.add_subparsers(dest="command")
    for command in ("setup-check", "demo", "walkthrough", "submit"):
        commands.add_parser(command)
    check = commands.add_parser("check")
    check.add_argument("--case", choices=CHECKS)
    run = commands.add_parser("run")
    run.add_argument("--case", default="alternatives")
    run.add_argument("--kind", choices=KINDS, default="schedule")
    for field in ("component", "section", "day"):
        run.add_argument("--" + field)
    run.add_argument("--block", action="append", default=[], help="Extra blocked interval: Tue,09:00,10:00")
    run.add_argument("--timeout", type=float, default=LIMIT_SECONDS)
    options = parser.parse_args()
    folder = options.submission.resolve()
    try:
        catalogue, requests = read_catalogue(DATA)
        if options.command == "setup-check":
            setup()
        elif options.command == "demo":
            demo(catalogue)
        elif options.command == "walkthrough":
            open_guide(WALKTHROUGH)
        elif options.command == "submit":
            notice(str(package(folder, ROOT / "output/submissions")), "Submission ZIP")
        elif options.command == "check":
            results = checks(folder, [options.case] if options.case else CHECKS)
            return int(any(result["status"] != "PASS" for result in results.values()))
        elif options.command == "run":
            if options.case not in requests or not 0.1 <= options.timeout <= 120:
                raise ValueError(f"Select a known request ({', '.join(requests)}) and a timeout from 0.1 to 120 seconds.")
            for block in options.block:
                meeting(block.split(","), catalogue.days)
            query = Query(options.kind, options.component, options.section, options.day)
            result = job(folder, "run", options.case, query, options.block, options.timeout)
            show_result(catalogue, query, result)
            return int(result["status"] not in EXPLANATIONS or result["status"] == "INCONCLUSIVE")
        else:
            return menu(folder, catalogue, requests, options.plain_menu)
    except (ValueError, OSError, SyntaxError) as error:
        notice(error, "Could not complete action", "yellow")
        return 2
    return 0
