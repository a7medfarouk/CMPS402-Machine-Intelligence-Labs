"""Implement the planning rules yourself; no world implementation is supplied."""

from campus.contracts import Problem, WorldState


ACTIONS = ("UP", "RIGHT", "DOWN", "LEFT")


class CampusProblem(Problem):
    def __init__(self, specification):
        self.map = specification

    def get_initial_state(self):
        """Return a hashable initial planning state."""
        raise NotImplementedError("Implement the initial state")

    def describe(self, state):
        """Convert your state into a WorldState for the supplied viewer/checker."""
        raise NotImplementedError("Implement the display adapter")

    def is_goal(self, state):
        raise NotImplementedError("Implement the goal test")

    def get_actions(self, state):
        """Return legal strings in ACTIONS order: UP, RIGHT, DOWN, LEFT; omit illegal moves."""
        raise NotImplementedError("Implement the legal actions")

    def get_successor(self, state, action):
        raise NotImplementedError("Implement the successor function")

    def get_cost(self, state, action):
        raise NotImplementedError("Implement the step cost")
