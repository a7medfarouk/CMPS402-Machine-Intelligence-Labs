"""Complete reset and step using your own CampusProblem; do not duplicate world rules."""

import gymnasium as gym
from gymnasium import spaces


ACTIONS = ("UP", "RIGHT", "DOWN", "LEFT")


class CampusCourierEnv(gym.Env):
    metadata = {"render_modes": ["ansi"]}

    def __init__(self, specification, max_steps=100, render_mode=None, model_class=None):
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        if render_mode not in (None, "ansi"):
            raise ValueError("Use render_mode=None or 'ansi'")
        if model_class is None:
            from submission.model import CampusProblem
            model_class = CampusProblem
        self.model = model_class(specification)
        self.max_steps = max_steps
        self.render_mode = render_mode
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Dict({"row": spaces.Discrete(specification.height), "column": spaces.Discrete(specification.width), "has_key": spaces.Discrete(2)})
        self._state = None
        self._steps = 0
        self._finished = True

    def _observation(self):
        description = self.model.describe(self._state)
        return {"row": int(description.row), "column": int(description.column), "has_key": int(description.has_key)}

    def _info(self):
        legal = self.model.get_actions(self._state)
        return {"action_mask": [int(action in legal) for action in ACTIONS], "steps": self._steps}

    def reset(self, *, seed=None, options=None):
        """Call super().reset(seed=seed); restore model initial state/counters; return observation, info."""
        raise NotImplementedError("Complete optional reset using your model")

    def step(self, action):
        """Return observation, reward, terminated, truncated, info under the guide's adapter contract."""
        raise NotImplementedError("Complete optional step using your model")

    def render(self):
        if self._state is None:
            raise RuntimeError("Call reset before render")
        rows = [list(row) for row in self.model.map.rows]
        description = self.model.describe(self._state)
        rows[description.row][description.column] = "@"
        return "\n".join("".join(row) for row in rows)
