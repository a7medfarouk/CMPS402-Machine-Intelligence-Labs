"""Consistent student-facing verdicts and concise diagnostic descriptions."""

import traceback

from .contracts import BudgetExceeded


class WrongAnswer(AssertionError):
    pass


LABELS = {"ok": "PASS", "no_solution": "NO SOLUTION", "wrong_answer": "WRONG ANSWER", "time_limit": "TIME LIMIT", "resource_limit": "RESOURCE LIMIT", "not_implemented": "NOT IMPLEMENTED", "runtime_error": "RUNTIME ERROR", "local_only": "LOCAL ONLY"}


def describe_error(error):
    if isinstance(error, NotImplementedError):
        status, hint = "not_implemented", "Complete the named function in submission/."
    elif isinstance(error, BudgetExceeded):
        status, hint = "resource_limit", "Check duplicate detection; the automatic expansion budget was exceeded."
    elif isinstance(error, AssertionError):
        status, hint = "wrong_answer", "Compare expected and actual behavior; rerun just this case."
    else:
        status, hint = "runtime_error", "Fix the exception before comparing algorithm performance."
    frames = traceback.extract_tb(error.__traceback__)
    student_frames = [frame for frame in frames if "submission" in frame.filename or "/reference/" in frame.filename.replace("\\", "/")]
    location = ""
    if isinstance(error, SyntaxError):
        location = f"{error.filename}:{error.lineno}"
    elif student_frames:
        location = f"{student_frames[-1].filename}:{student_frames[-1].lineno}"
    return {"status": status, "error": f"{type(error).__name__}: {error}", "hint": hint, "location": location}


def table(headers, rows):
    rows = [[str(value) for value in row] for row in rows]
    widths = [max(len(str(header)), *(len(row[index]) for row in rows)) for index, header in enumerate(headers)] if rows else [len(header) for header in headers]
    render = lambda row: "  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip()
    return "\n".join([render(headers), render(["-" * width for width in widths]), *[render(row) for row in rows]])
