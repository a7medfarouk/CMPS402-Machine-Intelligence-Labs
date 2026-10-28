"""Implement generic BFS, DFS, UCS, greedy, and A*; shared helpers are allowed."""

from campus.contracts import Node, Problem, reconstruct
from collections import deque

def BreadthFirstSearch(problem : Problem, initial_state):
    node = Node(initial_state)
    if problem.is_goal(node.state):
        return reconstruct(node)

    frontier = deque([node])
    frontier_states = {node.state}
    explored = set()

    while frontier:
        node = frontier.popleft()
        explored.add(node.state)

        for action in problem.get_actions(node.state):
            child_state = problem.get_successor(node.state, action)
            if not (child_state in explored or child_state in frontier_states):
                child = Node(child_state, node.cost + problem.get_cost(node.state, action), node, action)
                if problem.is_goal(child.state):
                    return reconstruct(child)
                frontier.append(child)
                frontier_states.add(child.state)

    return None


def DepthFirstSearch(problem, initial_state):
        node = Node(initial_state)
        if problem.is_goal(node.state):
            return reconstruct(node)

        frontier = deque([node])
        frontier_states = {node.state}
        explored = set()

        while frontier:
            node = frontier.pop()
            if problem.is_goal(node.state):
                return reconstruct(node)
            explored.add(node.state)

            for action in problem.get_actions(node.state):
                child_state = problem.get_successor(node.state, action)
                if not (child_state in explored or child_state in frontier_states):
                    child = Node(child_state, node.cost + problem.get_cost(node.state, action), node, action)
                    frontier.append(child)
                    frontier_states.add(child.state)

        return None


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
