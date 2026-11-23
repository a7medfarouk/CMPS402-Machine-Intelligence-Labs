"""Run submitted code through a narrow interface with a process time limit."""

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from types import ModuleType

from .catalogue import validate_query
from .contracts import Advice, BinaryConstraint, SolveResult, SolveStatus, UnaryConstraint, Verdict


ROOT = Path(__file__).resolve().parents[1]
LIMIT_SECONDS = 5


class IncorrectResult(ValueError):
    pass


class SearchLimit(Exception):
    pass


def load_part(folder, name):
    location = str(Path(folder).resolve())
    package_name = "_advisor_submission"
    if package_name not in sys.modules or sys.modules[package_name].__path__ != [location]:
        for key in tuple(sys.modules):
            if key == package_name or key.startswith(package_name + "."):
                del sys.modules[key]
        package = ModuleType(package_name)
        package.__path__ = [location]
        sys.modules[package_name] = package
    return import_module(package_name + "." + name)


def isolated(command, cwd=ROOT, timeout=LIMIT_SECONDS):
    try:
        process = subprocess.run(
            [sys.executable, *command], cwd=cwd, capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"status": "INCONCLUSIVE", "detail": f"Time limit ({timeout:g} seconds). No feasibility conclusion."}
    if process.returncode:
        return {"status": "RUNTIME ERROR", "detail": (process.stderr.strip().splitlines() or ["Worker stopped without a result."])[-1][:450]}
    try:
        result = json.loads(process.stdout)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError
        return result
    except ValueError:
        return {"status": "RUNTIME ERROR", "detail": "Worker returned no readable result."}


def emit(work):
    try:
        with open(os.devnull, "w", encoding="utf-8") as sink, redirect_stdout(sink), redirect_stderr(sink):
            result = work()
    except NotImplementedError as error:
        result = {"status": "NOT IMPLEMENTED", "detail": str(error)}
    except (AssertionError, IncorrectResult) as error:
        result = {"status": "WRONG ANSWER", "detail": str(error)}
    except Exception as error:
        result = {"status": "RUNTIME ERROR", "detail": f"{type(error).__name__}: {error}"}
    print(json.dumps(result, ensure_ascii=False))


def schedule_shape(catalogue, request, schedule):
    return (
        isinstance(schedule, dict) and set(schedule) == set(request.components)
        and all(any(section.identifier == value for section in catalogue.sections[component])
                for component, value in schedule.items())
    )


def observe(problem, deadline, counters):
    def checked(condition):
        def wrapped(*values):
            if perf_counter() > deadline:
                raise SearchLimit
            counters["constraint_checks"] += 1
            return condition(*values)
        return wrapped

    problem.constraints = [
        UnaryConstraint(constraint.variable, checked(constraint.condition))
        if isinstance(constraint, UnaryConstraint)
        else BinaryConstraint(constraint.variables, checked(constraint.condition))
        for constraint in problem.constraints
    ]
    complete = problem.is_complete

    def observed_complete(assignment):
        if perf_counter() > deadline:
            raise SearchLimit
        counters["completion_checks"] += 1
        return complete(assignment)

    problem.is_complete = observed_complete


def execute(catalogue, request, query, build_problem, solve, answer_query, timeout=LIMIT_SECONDS, validator=None):
    try:
        validate_query(catalogue, request, query)
    except ValueError as error:
        return {"status": "INVALID REQUEST", "detail": str(error)}
    start = perf_counter()
    deadline = start + timeout
    runs = []

    def solve_request(allowed):
        counters = {"constraint_checks": 0, "completion_checks": 0}
        began = perf_counter()
        runs.append({"restriction": {component: sorted(values) for component, values in allowed.items()}, **counters})
        try:
            if perf_counter() > deadline:
                raise SearchLimit
            if set(allowed) - set(request.components):
                raise IncorrectResult("A restriction names a component outside the request.")
            problem = build_problem(catalogue, request)
            for component, values in allowed.items():
                problem.domains[component] = problem.domains[component] & set(values)
            observe(problem, deadline, counters)
            schedule = solve(problem)
            if perf_counter() > deadline:
                raise SearchLimit
            if schedule is None:
                return SolveResult(SolveStatus.UNSAT)
            if not schedule_shape(catalogue, request, schedule) or any(schedule[key] not in values for key, values in allowed.items()):
                raise IncorrectResult("The solver returned an incomplete, unknown, or restricted-out section.")
            if validator is not None and not validator(catalogue, request, schedule):
                raise IncorrectResult("The schedule violates catalogue constraints.")
            return SolveResult(SolveStatus.SAT, schedule)
        except SearchLimit:
            return SolveResult(SolveStatus.LIMIT)
        finally:
            runs[-1].update(counters, milliseconds=round((perf_counter() - began) * 1000, 2))

    if query.kind == "schedule":
        result = solve_request({})
        advice = Advice({SolveStatus.SAT: Verdict.SCHEDULE, SolveStatus.UNSAT: Verdict.BASE_INFEASIBLE,
                         SolveStatus.LIMIT: Verdict.INCONCLUSIVE}[result.status], result.schedule)
    else:
        advice = answer_query(catalogue, request, query, solve_request)
    allowed_verdicts = {
        "schedule": {Verdict.SCHEDULE}, "take": {Verdict.POSSIBLE, Verdict.IMPOSSIBLE},
        "avoid-day": {Verdict.POSSIBLE, Verdict.IMPOSSIBLE},
        "unavoidable": {Verdict.NOT_UNAVOIDABLE, Verdict.UNAVOIDABLE},
    }[query.kind] | {Verdict.BASE_INFEASIBLE, Verdict.INCONCLUSIVE}
    if not isinstance(advice, Advice) or advice.verdict not in allowed_verdicts:
        raise IncorrectResult("Return an Advice with a verdict appropriate to the question.")
    if advice.verdict in {Verdict.SCHEDULE, Verdict.POSSIBLE, Verdict.NOT_UNAVOIDABLE}:
        if not schedule_shape(catalogue, request, advice.schedule):
            raise IncorrectResult("This answer needs a complete witness schedule.")
        if not satisfies_query(catalogue, advice.schedule, query):
            raise IncorrectResult("The witness does not meet the requested hypothetical restriction.")
        if validator is not None and not validator(catalogue, request, advice.schedule):
            raise IncorrectResult("The witness violates the base request.")
    elif advice.schedule is not None:
        raise IncorrectResult("Do not attach a schedule to this verdict.")
    return {"status": advice.verdict, "schedule": advice.schedule, "runs": runs}


def satisfies_query(catalogue, schedule, query):
    if query.kind == "schedule":
        return True
    if query.kind == "take":
        return schedule[query.component] == query.section
    if query.kind == "unavoidable":
        return schedule[query.component] != query.section
    for component, value in schedule.items():
        section = next(section for section in catalogue.sections[component] if section.identifier == value)
        if section.meeting.day == query.day:
            return False
    return True
