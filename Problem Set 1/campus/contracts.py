"""Problem contracts and automatic expansion recording; no frontier implementation."""

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Hashable


class BudgetExceeded(RuntimeError):
    pass


class Problem:
    """Planning model interface, with supplied adapters for the replay tools."""

    @property
    def initial(self):
        return self.get_initial_state()

    def get_initial_state(self):
        raise NotImplementedError

    def get_actions(self, state):
        raise NotImplementedError

    def get_successor(self, state, action):
        raise NotImplementedError

    def get_cost(self, state, action):
        return 1

    def successors(self, state):
        return [(action, self.get_successor(state, action), self.get_cost(state, action)) for action in self.get_actions(state)]


@dataclass(frozen=True)
class WorldState:
    row: int
    column: int
    has_key: bool = False


@dataclass(frozen=True)
class Node:
    state: Hashable
    cost: float = 0
    parent: Any = None
    action: str | None = None


def reconstruct(node):
    actions = []
    while node.parent is not None:
        actions.append(node.action)
        node = node.parent
    return list(reversed(actions))


@dataclass
class Observer:
    max_expansions: int = 10000
    expanded: list = field(default_factory=list)

    def expand(self, state):
        if len(self.expanded) >= self.max_expansions:
            raise BudgetExceeded("Expansion budget exceeded")
        self.expanded.append(state)

class ObservedProblem:
    """Wrap a planning model; successor calls, not student counters, record work."""

    def __init__(self, model, observer=None):
        self.model = model
        self.observer = observer or Observer()
        self.initial = model.initial
        hash(self.initial)
        self.in_heuristic = False
        self.transition_cache = {}

    def get_initial_state(self):
        return self.initial

    def get_actions(self, state):
        transitions = self.successors(state)
        self.transition_cache[state] = {action: (successor, cost) for action, successor, cost in transitions}
        return [action for action, successor, cost in transitions]

    def get_successor(self, state, action):
        if state in self.transition_cache:
            return self.transition_cache[state][action][0]
        if hasattr(self.model, "get_successor"):
            return self.model.get_successor(state, action)
        return next(successor for candidate, successor, cost in self.model.successors(state) if candidate == action)

    def get_cost(self, state, action):
        if state in self.transition_cache:
            return self.transition_cache[state][action][1]
        if hasattr(self.model, "get_cost"):
            return self.model.get_cost(state, action)
        return next(cost for candidate, successor, cost in self.model.successors(state) if candidate == action)

    @property
    def map(self):
        return self.model.map

    def describe(self, state):
        return self.model.describe(state)

    def is_goal(self, state):
        return self.model.is_goal(state)

    def successors(self, state):
        if self.in_heuristic:
            raise ValueError("Heuristics must not call the search successor function")
        self.observer.expand(state)
        transitions = list(self.model.successors(state))
        for action, successor, cost in transitions:
            hash(successor)
            if not isinstance(cost, (int, float)) or not isfinite(cost) or cost <= 0:
                raise ValueError("Step costs must be positive finite numbers")
        return transitions

    def checked_heuristic(self, function):
        def estimate(state):
            self.in_heuristic = True
            try:
                value = function(self, state)
                if not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                    raise ValueError("Heuristics must be finite and nonnegative")
                return value
            finally:
                self.in_heuristic = False
        return estimate
