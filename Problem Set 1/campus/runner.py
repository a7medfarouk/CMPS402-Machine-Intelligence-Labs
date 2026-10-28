"""Local diagnostics using student-model replay and published reference facts."""

from dataclasses import asdict
import json
from math import isfinite
from pathlib import Path
from time import perf_counter

from .baselines import manhattan
from .contracts import ObservedProblem, Observer
from .feedback import WrongAnswer, describe_error


def reference_fact(specification):
    path = Path(__file__).resolve().parents[1] / "maps/public-facts.json"
    if not path.exists():
        return None
    return next((case for case in json.loads(path.read_text(encoding="utf-8")) if tuple(case["rows"]) == specification.rows), None)


def empty_record(specification, algorithm, heuristic_name):
    return {"schema": 4, "map": list(specification.rows), "algorithm": algorithm, "heuristic": heuristic_name, "status": "runtime_error", "actions": None, "cost": None, "length": None, "path": [], "expanded": [], "expansions": 0, "seconds": 0, "validation_scope": "Public checks and replay through your model; hidden grading uses a separate private world implementation."}


def replay_model(model, actions):
    if not isinstance(actions, list):
        raise WrongAnswer("Return a list of action strings, or None if unreachable.")
    state, cost = model.initial, 0
    states = [state]
    cumulative = [0]
    for index, action in enumerate(actions):
        if model.is_goal(state):
            raise WrongAnswer(f"Route contains extra actions after completion, at move {index + 1}.")
        if action not in model.get_actions(state):
            raise WrongAnswer(f"Move {index + 1}: {action!r} is not legal in your planning model.")
        weight = model.get_cost(state, action)
        if not isinstance(weight, (int, float)) or not isfinite(weight) or weight <= 0:
            raise WrongAnswer(f"Move {index + 1}: step cost must be positive and finite.")
        cost += weight
        state = model.get_successor(state, action)
        states.append(state)
        cumulative.append(cost)
    if not model.is_goal(state):
        raise WrongAnswer("Your route ends before the goal condition is satisfied.")
    return states, cost, cumulative


def execute(specification, bundle, algorithm="astar", heuristic_name="baseline", max_expansions=10000):
    observer = Observer(max_expansions=max_expansions)
    document = empty_record(specification, algorithm, heuristic_name)
    fact = reference_fact(specification)
    started = perf_counter()
    problem = None
    try:
        problem = ObservedProblem(bundle.Model(specification), observer)
        estimate = problem.checked_heuristic(bundle.heuristic if heuristic_name == "student" else manhattan)
        actions = bundle.solve(problem, algorithm, estimate)
        if actions is None:
            if fact is not None and fact["optimal_cost"] is not None:
                raise WrongAnswer("This supplied map has a solution, but your search returned None.")
            document["status"] = "no_solution"
            if fact is None:
                document["status"] = "local_only"
                document["hint"] = "No published oracle for this custom map. The no-solution claim is not independently certified."
        else:
            states, cost, cumulative = replay_model(problem.model, actions)
            document.update(actions=actions, cost=cost, length=len(actions))
            if fact is not None:
                if fact["optimal_cost"] is None:
                    raise WrongAnswer("This supplied map is unreachable, but your model/search returned a route.")
                if cost < fact["optimal_cost"] or (algorithm in {"ucs", "astar"} and cost != fact["optimal_cost"]):
                    raise WrongAnswer(f"Expected optimal cost {fact['optimal_cost']}; received cost {cost}. Check costs, transitions, and priority updates.")
                if algorithm == "bfs" and len(actions) != fact["minimum_steps"]:
                    raise WrongAnswer(f"BFS should return {fact['minimum_steps']} moves; received {len(actions)}.")
            document.update(status="ok", path=[{**asdict(problem.describe(state)), "cost_so_far": total} for state, total in zip(states, cumulative)])
            if fact is None:
                document.update(status="local_only", hint="Custom map: replay is checked against your model only. Run public model tests; staff grading uses an independent private world.")
    except Exception as error:
        document.update(describe_error(error))
    if problem is not None:
        try:
            document["expanded"] = [asdict(problem.describe(state)) for state in observer.expanded]
        except Exception as error:
            if not document.get("error"):
                document.update(describe_error(error))
    document.update(seconds=perf_counter() - started, expansions=len(observer.expanded))
    return document
