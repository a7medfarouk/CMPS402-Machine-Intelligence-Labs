"""Local worker entry point. No grading answers are stored here."""

import argparse
from dataclasses import replace

from .catalogue import Query, meeting, read_catalogue
from .checks import CHECKS, run_check
from .execution import ROOT, emit, execute, load_part


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("operation", choices=("check", "run"))
    parser.add_argument("case")
    parser.add_argument("--kind", default="schedule")
    parser.add_argument("--component")
    parser.add_argument("--section")
    parser.add_argument("--day")
    parser.add_argument("--block", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=5)
    options = parser.parse_args()

    def work():
        catalogue, requests = read_catalogue(ROOT / "data/timetable.json")
        if options.operation == "check":
            return run_check(options.case, options.folder, catalogue, requests)
        request = requests[options.case]
        request = replace(request, unavailable=(*request.unavailable, *(meeting(block.split(","), catalogue.days) for block in options.block)))
        query = Query(options.kind, options.component, options.section, options.day)

        def build(*values):
            return load_part(options.folder, "model").build_problem(*values)

        def solve(problem):
            return load_part(options.folder, "solver").solve(problem)

        def answer(*values):
            return load_part(options.folder, "advisor").answer_query(*values)

        return execute(catalogue, request, query, build, solve, answer, timeout=options.timeout)

    emit(work)


if __name__ == "__main__":
    main()
