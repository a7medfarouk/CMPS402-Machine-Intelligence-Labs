"""Implement the planning rules yourself; no world implementation is supplied."""

from campus.contracts import Problem, WorldState
from campus.maps import MapSpec

ACTIONS = ("UP", "RIGHT", "DOWN", "LEFT")
STEPS = {"UP": (-1, 0), "RIGHT": (0, 1), "DOWN": (1, 0), "LEFT": (0, -1)}


class CampusProblem(Problem):
    def __init__(self, specification):
        self.map: MapSpec = specification

    def get_initial_state(self):
        """Return a hashable initial planning state."""
        row, column = self.map.start
        return WorldState(row, column, False)

    def describe(self, state):
        """Convert your state into a WorldState for the supplied viewer/checker."""
        return WorldState(state.row, state.column, state.has_key)

    def is_goal(self, state):
        at_goal = (state.row, state.column) == tuple(self.map.goal)
        return at_goal and (state.has_key or self.map.pickup is None)

    def get_actions(self, state):
        """Return legal strings in ACTIONS order: UP, RIGHT, DOWN, LEFT; omit illegal moves."""
        if self.is_goal(state):
            return []
        
        legal_actions = []

        for action in ACTIONS:
            r = state.row + STEPS[action][0]
            c = state.column + STEPS[action][1]
            if not (0 <= r < self.map.height and 0 <= c < self.map.width):
                continue
            tile = self.map.rows[r][c]
            if tile == "#" or (tile == "D" and not state.has_key):
                continue
            legal_actions.append(action)

        return legal_actions

    def get_successor(self, state, action):
        row = state.row + STEPS[action][0]
        column = state.column + STEPS[action][1]
        has_key = state.has_key or self.map.rows[row][column] == "K"

        return WorldState(row, column, has_key)

    def get_cost(self, state, action):
        row = state.row + STEPS[action][0]
        column = state.column + STEPS[action][1]

        return 5 if self.map.rows[row][column] == "w" else 1
        