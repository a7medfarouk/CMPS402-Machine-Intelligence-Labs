"""Implement generic BFS, DFS, UCS, greedy, and A*; shared helpers are allowed."""

from campus.contracts import Node, reconstruct


def BreadthFirstSearch(problem, initial_state):
    raise NotImplementedError("Implement graph BFS")


def DepthFirstSearch(problem, initial_state):
    raise NotImplementedError("Implement graph DFS")


def UniformCostSearch(problem, initial_state):
    raise NotImplementedError("Implement UCS")


def AStarSearch(problem, initial_state, heuristic):
    raise NotImplementedError("Implement A*")


def BestFirstSearch(problem, initial_state, heuristic):
    raise NotImplementedError("Implement greedy best-first search")


def solve(problem, algorithm="astar", heuristic=None):
    """Supplied dispatcher; implement the five entry points above."""
    functions = {"bfs": BreadthFirstSearch, "dfs": DepthFirstSearch, "ucs": UniformCostSearch, "greedy": BestFirstSearch, "astar": AStarSearch}
    if algorithm not in functions:
        raise ValueError(algorithm)
    initial_state = problem.get_initial_state()
    if algorithm in {"greedy", "astar"}:
        estimate = heuristic or (lambda state: 0)
        return functions[algorithm](problem, initial_state, lambda current_problem, state: estimate(state))
    return functions[algorithm](problem, initial_state)
