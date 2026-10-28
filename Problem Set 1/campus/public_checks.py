"""Public checks include worked microcases, but no search implementations."""

from .checking import GraphProblem, assert_condition, bfs_duplicate_check, evaluate_checks, graph_run, priority_graph, priority_tie_check, validate_examples
from .contracts import ObservedProblem, WorldState
from .maps import MapSpec


TITLES = ["Model: weighted movement", "Model: key possession and revisit", "Model: destination before pickup", "Model: blocked key and unreachable map", "BFS: priority and generation-time goal", "DFS: priority behavior", "UCS: priority behavior", "Greedy: priority behavior", "A*: priority behavior", "BFS: duplicate suppression", "FIFO priority ties", "Initial goals and unreachable cycles", "Heuristic: pickup bound and consistency", "Heuristic: portable describe interface"]


def portable_heuristic_check(function):
    class DescriptionProblem:
        map = MapSpec(("S....G", "......", "K....."))

        def __init__(self):
            self.states = {object(): description for description in (WorldState(0, 0, False), WorldState(2, 0, True), WorldState(0, 5, True))}
            self.description_calls = 0

        def describe(self, state):
            self.description_calls += 1
            return self.states[state]

        def is_goal(self, state):
            return self.states[state] == WorldState(0, 5, True)

    problem = DescriptionProblem()
    try:
        values = [function(problem, state) for state in problem.states]
    except (AttributeError, TypeError, KeyError) as error:
        assert_condition(False, f"Use problem.describe(state) inside heuristic; do not access your model's state fields, tuple positions, or model-only attributes. State representations differ in staff checks. Original error: {type(error).__name__}: {error}")
    assert_condition(problem.description_calls > 0, "Use problem.describe(state) rather than depending on your model's state definition.")
    assert_condition(all(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < float('inf') for value in values), "Portable heuristic values must be finite nonnegative numbers")
    assert_condition(5 < values[0] <= 9 and values[1] <= 7 and values[2] == 0, "Portable describe test: expected a pickup-aware start estimate in (5, 9], a post-pickup estimate at most 7, and zero at the completed goal.")


def checks(bundle):
    def model_case(rows):
        validate_examples(MapSpec(tuple(rows)), bundle.Model)

    def algorithm_case(algorithm, expected_actions, expected_expansions):
        actions, observer = graph_run(bundle, priority_graph(), algorithm)
        allowed = [(expected_actions, expected_expansions)]
        if algorithm == "dfs":
            allowed.append((["near", "finish"], ["start", "near"]))
        assert_condition((actions, observer.expanded) in allowed, f"Expected one of {allowed}; got actions={actions}, expansions={observer.expanded}")

    def edge_cases():
        for algorithm in ("bfs", "dfs", "ucs", "greedy", "astar"):
            actions, observer = graph_run(bundle, GraphProblem({}, initial="goal"), algorithm)
            assert_condition(actions == [] and not observer.expanded, "An initial goal needs an empty path and no expansion")
            graph = GraphProblem({"start": [("loop", "loop", 1)], "loop": [("back", "start", 1)]})
            actions, observer = graph_run(bundle, graph, algorithm)
            assert_condition(actions is None, "A finite unreachable cycle must terminate with None")

    def heuristic_case():
        specification = MapSpec(("S....G", "......", "K....."))
        model, states = validate_examples(specification, bundle.Model)
        problem = ObservedProblem(model)
        estimate = problem.checked_heuristic(bundle.heuristic)
        start_value = estimate(problem.initial)
        assert_condition(5 < start_value <= 9, "This published case needs a pickup-aware lower bound stronger than direct Manhattan")
        for state in states:
            value = estimate(state)
            if problem.is_goal(state):
                assert_condition(value == 0, "The heuristic must be zero at a goal")
            for action, successor, cost in model.successors(state):
                assert_condition(value <= cost + estimate(successor), "Inconsistent heuristic on a reachable edge")

    functions = [
        ("model: weighted movement", lambda: model_case(["SwG", "..."])),
        ("model: key possession and revisit", lambda: model_case(["K.SDG"])),
        ("model: destination before pickup", lambda: model_case(["SG.K"])),
        ("model: blocked key and unreachable map", lambda: [model_case(rows) for rows in (["SDKG"], ["S#G"])]),
        ("BFS priority and generation-time goal test", lambda: algorithm_case("bfs", ["near", "finish"], ["start", "near"])),
        ("DFS priority behavior", lambda: algorithm_case("dfs", ["detour", "via", "finish"], ["start", "detour", "via"])),
        ("UCS priority behavior", lambda: algorithm_case("ucs", ["detour", "via", "finish"], ["start", "detour", "via", "near"])),
        ("greedy priority behavior", lambda: algorithm_case("greedy", ["near", "finish"], ["start", "near"])),
        ("A* priority behavior", lambda: algorithm_case("astar", ["detour", "via", "finish"], ["start", "near", "detour", "via"])),
        ("BFS reached/frontier duplicate suppression", lambda: bfs_duplicate_check(bundle)),
        ("FIFO priority ties", lambda: [priority_tie_check(bundle, algorithm) for algorithm in ("ucs", "astar", "greedy")]),
        ("initial goals and unreachable cycles", edge_cases),
        ("heuristic: published pickup case and consistency", heuristic_case),
        ("heuristic: portable describe interface", lambda: portable_heuristic_check(bundle.heuristic)),
    ]
    return [(title, function) for title, (old_title, function) in zip(TITLES, functions)]


def run(bundle):
    return evaluate_checks(checks(bundle))
