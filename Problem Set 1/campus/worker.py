"""Disposable worker for local student runs; not a security sandbox."""

import json
import sys

from .feedback import describe_error
from .loading import load_bundle
from .maps import MapSpec
from .runner import execute


def main():
    request = json.loads(sys.stdin.read())
    try:
        bundle = load_bundle(request["submission"])
        if request["task"] == "run":
            result = execute(MapSpec(tuple(request["rows"])), bundle, request["algorithm"], request["heuristic"], request.get("max_expansions", 10000))
        else:
            from .checking import evaluate_checks
            from .public_checks import checks
            result = evaluate_checks([checks(bundle)[request["index"]]])["checks"][0]
    except Exception as error:
        result = {"passed": False, **describe_error(error)}
    print("__CAMPUS_RESULT__" + json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
