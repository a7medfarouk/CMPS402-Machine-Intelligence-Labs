"""Supplied heuristic baseline; no search algorithms are supplied."""


def manhattan(problem, state):
    description = problem.describe(state)
    goal_row, goal_column = problem.map.goal
    return abs(description.row - goal_row) + abs(description.column - goal_column)
