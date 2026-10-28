"""Public model diagnostics; checks validate rules, not a required representation."""

from dataclasses import asdict
import json
from pathlib import Path

from .contracts import WorldState
from .feedback import WrongAnswer, describe_error


def validate_examples(specification, model_class):
    fixtures = json.loads((Path(__file__).resolve().parents[1] / "maps/public-model-examples.json").read_text(encoding="utf-8"))
    examples = next(case["examples"] for case in fixtures if tuple(case["rows"]) == specification.rows)
    model, states = model_class(specification), []
    for example in examples:
        state = model.initial
        for action in example["prefix"]:
            state = model.get_successor(state, action)
        hash(state)
        description = model.describe(state)
        assert_condition(isinstance(description, WorldState) and asdict(description) == example["state"], f"Expected state {example['state']}; got {description!r}")
        assert_condition(model.is_goal(state) == example["is_goal"], f"Wrong goal test at {description!r}")
        transitions = list(model.successors(state))
        actual = [{"action": action, "state": asdict(model.describe(successor)), "cost": cost} for action, successor, cost in transitions]
        assert_condition(actual == example["transitions"], f"At {description!r}: expected {example['transitions']}; got {actual}")
        states.append(state)
    return model, states


class GraphProblem:
    """Tiny fully specified graphs used to distinguish algorithm behavior."""

    def __init__(self, edges, initial="start", goal="goal", estimates=None):
        self.edges = edges
        self.initial = initial
        self.goal = goal
        self.estimates = estimates or {}

    def is_goal(self, state):
        return state == self.goal

    def successors(self, state):
        return self.edges.get(state, [])

    def describe(self, state):
        return state

    def estimate(self, state):
        return self.estimates.get(state, 0)


def graph_run(bundle, graph, algorithm):
    from .contracts import ObservedProblem
    problem = ObservedProblem(graph)
    actions = bundle.solve(problem, algorithm, graph.estimate)
    return actions, problem.observer


def priority_graph():
    return GraphProblem({"start": [("near", "near", 3), ("detour", "detour", 1)], "near": [("finish", "goal", 3)], "detour": [("via", "via", 1)], "via": [("finish", "goal", 1)]}, estimates={"start": 3, "near": 0, "detour": 2, "via": 1})


def priority_tie_check(bundle, algorithm):
    if algorithm == "ucs":
        graph = GraphProblem({"start": [("first", "zeta", 1), ("second", "alpha", 1)], "zeta": [("finish", "goal", 100)], "alpha": [("finish", "goal", 1)]})
    elif algorithm == "astar":
        graph = GraphProblem({"start": [("first", "zeta", 4), ("second", "alpha", 1)], "zeta": [("finish", "goal", 2)], "alpha": [("finish", "goal", 4)]}, estimates={"zeta": 1, "alpha": 4})
    else:
        graph = GraphProblem({"start": [("first", "zeta", 9), ("second", "alpha", 1)], "zeta": [("finish", "goal", 1)], "alpha": [("finish", "goal", 1)]}, estimates={"zeta": 1, "alpha": 1})
    actions, observer = graph_run(bundle, graph, algorithm)
    expected = ["start", "zeta"] if algorithm == "greedy" else ["start", "zeta", "alpha"]
    assert_condition(observer.expanded == expected, "Priority ties must use enqueue order, not g, state sorting, or reversed actions")


def bfs_duplicate_check(bundle):
    graph = GraphProblem({"start": [("first", "first", 1), ("second", "second", 1)], "first": [("meet", "junction", 1)], "second": [("meet", "junction", 1)]})
    actions, observer = graph_run(bundle, graph, "bfs")
    assert_condition(actions is None, "This diamond has no goal")
    assert_condition(observer.expanded == ["start", "first", "second", "junction"], "BFS must expand this diamond in FIFO order without expanding its shared state twice")


def assert_condition(condition, message):
    if not condition:
        raise WrongAnswer(message)


def evaluate_checks(checks):
    outcomes = []
    for title, function in checks:
        try:
            function()
            outcomes.append({"check": title, "passed": True, "status": "ok"})
        except Exception as error:
            outcomes.append({"check": title, "passed": False, **describe_error(error)})
    return {"passed": sum(outcome["passed"] for outcome in outcomes), "total": len(outcomes), "checks": outcomes, "scope": "correctness evidence only; not a final mark or proof of algorithm authorship"}
