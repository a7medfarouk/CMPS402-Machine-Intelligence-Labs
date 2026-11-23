"""CMPS402 adversarial search assignment."""

import argparse
from pathlib import Path
import webbrowser

from game_lab.checks import BONUS_CHECKS, CHECKS, PUBLIC_CHECKS
from game_lab.packaging import package, save_members
from game_lab.server import serve
from game_lab.terminal import choose, notice, show_table, verdict
from game_lab.worker import ROOT, call


SUBMISSION = ROOT / "submission"
BONUS_GROUP = "chomp-endgame"


def checks(names, previous=None):
    results = {} if previous is None else previous.copy()
    for name in names:
        results[name] = call({"action": "check", "case": name})
    bonus = all(name in BONUS_CHECKS for name in results)
    title = "Chomp bonus" if bonus else "Public checks"
    show_table(("Check", "Outcome", "Detail"), [
        (BONUS_CHECKS[name][0] if bonus else name,
         verdict(item["status"]), item.get("detail", PUBLIC_CHECKS[name][0]))
        for name, item in results.items()
    ], title)
    passed = sum(item["status"] == "PASS" for item in results.values())
    if bonus:
        notice(f"Passed {passed}/{len(results)} checks. Your TA awards the bonus during the discussion.",
               "Chomp bonus")
    else:
        notice(f"Passed {passed}/{len(results)}.")
    return results


def check_menu(names, plain):
    results = checks(names)
    options = ("Re-run all public checks", "Re-run failed checks", "Choose one check")
    while (selected := choose("Public check results", options, plain)) is not None:
        if selected == 0:
            results = checks(names)
        elif selected == 1:
            failed = [name for name, item in results.items() if item["status"] != "PASS"]
            if failed:
                results = checks(failed, results)
            else:
                notice("All shown checks passed.")
        else:
            index = choose("Public check", [CHECKS[name][0] for name in names], plain)
            if index is not None:
                results = checks([names[index]], results)


def make_zip():
    path = package(SUBMISSION, ROOT / "output" / "submissions")
    notice(path, "Submission ZIP")


def submit(plain):
    selected = choose("Submit", ("Enter member details", "Build the Python-only ZIP"), plain)
    if selected == 0:
        choice = choose("Team size", ("One member", "Two members"), plain)
        if choice is not None:
            members = [{"name": input(f"Member {index} full name: ").strip(), "id": input(f"Member {index} ID: ").strip()}
                       for index in range(1, choice + 2)]
            save_members(SUBMISSION, members)
            notice("Member details saved.")
    elif selected == 1:
        make_zip()


def menu(plain):
    while True:
        try:
            action = choose("CMPS402 | Adversarial Search", ("Play in browser", "Run public checks",
                              "Chomp bonus", "Read instructions", "Submit"), plain, "Exit")
            if action is None:
                return 0
            if action == 0:
                serve()
            elif action == 1:
                check_menu(tuple(CHECKS), plain)
            elif action == 2:
                checks(BONUS_CHECKS)
            elif action == 3:
                path = ROOT / "Instructions.html"
                notice(path)
                webbrowser.open(path.as_uri())
            else:
                submit(plain)
        except (ValueError, OSError, SyntaxError) as error:
            notice(error, "Could not complete action", "yellow")
        except KeyboardInterrupt:
            notice("Action cancelled.")
        except EOFError:
            return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plain-menu", action="store_true")
    commands = parser.add_subparsers(dest="command")
    play = commands.add_parser("play")
    play.add_argument("--port", type=int, default=0)
    play.add_argument("--no-browser", action="store_true")
    check = commands.add_parser("check")
    check.add_argument("--case", choices=(*PUBLIC_CHECKS, BONUS_GROUP))
    commands.add_parser("submit")
    args = parser.parse_args()
    try:
        if args.command == "play":
            serve(args.port, not args.no_browser)
        elif args.command == "check":
            names = CHECKS
            if args.case == BONUS_GROUP:
                names = BONUS_CHECKS
            elif args.case:
                names = (args.case,)
            return int(any(item["status"] != "PASS" for item in checks(names).values()))
        elif args.command == "submit":
            make_zip()
        else:
            return menu(args.plain_menu)
    except (ValueError, OSError, SyntaxError) as error:
        notice(error, "Could not complete action", "yellow")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
