"""Evaluate one game request or unit check in a separate Python process."""

from contextlib import redirect_stdout
from importlib import import_module
import json
import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from .checks import EVALUATION_CHECKS, PUBLIC_CHECKS
from .games import GAMES, PRESETS, baseline, preset_game, replay, zero


ROOT = Path(__file__).resolve().parents[1]
SEARCH_LIMIT = 8


def call(request, seconds=SEARCH_LIMIT):
    try:
        result = subprocess.run([sys.executable, "-m", "game_lab.worker"], input=json.dumps(request),
                                cwd=ROOT, encoding="utf-8", capture_output=True, timeout=seconds)
    except subprocess.TimeoutExpired:
        if request.get("action") == "check":
            return {"status": "TIME LIMIT", "detail": f"This check exceeded {seconds} seconds. Review stopping conditions and repeated work."}
        return {"status": "TIME LIMIT", "detail": f"The run took more than {seconds} seconds. Try a lower depth."}
    if result.returncode:
        return {"status": "RUNTIME ERROR", "detail": (result.stderr.strip().splitlines() or ["Worker stopped."])[-1][:240]}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"status": "RUNTIME ERROR", "detail": "The worker did not return a readable result."}


class ObservedGame:
    def __init__(self, game, evaluate):
        self.game = game
        self.estimate = evaluate
        self.counts = {"terminal_checks": 0, "successors": 0, "evaluations": 0}

    def is_terminal(self, state):
        self.counts["terminal_checks"] += 1
        return self.game.is_terminal(state)

    def get_successor(self, state, action):
        self.counts["successors"] += 1
        return self.game.get_successor(state, action)

    def evaluate(self, _, state, max_player):
        self.counts["evaluations"] += 1
        value = self.estimate(self.game, state, max_player)
        if type(value) not in (int, float) or not math.isfinite(value) or not -1000 < value < 1000:
            raise AssertionError("Your evaluator must return a finite score between -1000 and 1000.")
        return value

    def __getattr__(self, name):
        return getattr(self.game, name)


def decide(game_name, game, state, request, method):
    mode = request["agent"]
    if mode == "baseline":
        began = perf_counter()
        value, move = baseline(game, state)
        return {"method": method, "value": value, "move": move, "milliseconds": round((perf_counter() - began) * 1000, 2)}
    if mode != "student":
        raise ValueError("Choose a known opponent.")
    search = import_module("submission.search")
    estimate = zero
    if request["evaluation"] == "student":
        evaluation = import_module("submission.evaluation")
        estimate = getattr(evaluation, f"evaluate_{game_name.replace('-', '_')}")
    observed = ObservedGame(game, estimate)
    depth = request["depth"]
    began = perf_counter()
    if method == "minimax":
        value, move = search.minimax(observed, state, observed.evaluate, depth, state.turn)
    else:
        value, move = search.alphabeta(observed, state, observed.evaluate, depth, state.turn, ordered=method == "ordered")
    if type(value) not in (int, float) or not math.isfinite(value):
        raise AssertionError("Return a finite score.")
    if move not in game.get_actions(state):
        raise AssertionError("The agent did not return a legal move.")
    return {"method": method, "value": value, "move": move, "max_player": state.turn,
            "milliseconds": round((perf_counter() - began) * 1000, 2), **observed.counts}


def game_request(request):
    game_name = request["game"]
    preset = request["preset"]
    game = preset_game(game_name, preset)
    opening = PRESETS[game_name][preset]
    depth = request["depth"]
    if type(depth) is not int or not 1 <= depth <= 4:
        raise ValueError("Depth must be from 1 to 4.")
    if request["method"] not in {"minimax", "alphabeta", "ordered"} or request["evaluation"] not in {"student", "zero"}:
        raise ValueError("Unknown search or evaluation mode.")
    raw = request["history"]
    if not isinstance(raw, list) or len(raw) > game.rows * game.columns:
        raise ValueError("Invalid move history.")
    if game_name == "connect-four":
        valid = all(type(move) is int and 0 <= move < game.columns for move in raw)
        moves = tuple(raw)
    else:
        valid = all(isinstance(move, list) and len(move) == 2 and
                    all(type(value) is int for value in move)
                    and 0 <= move[0] < game.rows and 0 <= move[1] < game.columns for move in raw)
        moves = tuple(tuple(move) for move in raw) if valid else ()
    if not valid:
        raise ValueError("Invalid move history.")
    state = replay(game, game.initial, opening)
    state = replay(game, state, moves)
    ended, utilities = game.is_terminal(state)
    if request["action"] == "compare":
        if ended:
            raise ValueError("Load a playable position before comparing.")
        stats = decide(game_name, game, state, {**request, "agent": "student"}, request["method"])
        return {"status": "OK", "stats": stats}

    statistics = None
    if request["action"] == "reply" and not ended:
        statistics = decide(game_name, game, state, request, request["method"])
        moves = (*moves, statistics["move"])
        state = game.get_successor(state, statistics["move"])
        ended, utilities = game.is_terminal(state)
    result = None if not ended else "draw" if utilities[0] == 0 else 0 if utilities[0] > 0 else 1
    return {"status": "OK", "board": state.board, "rows": game.rows, "columns": game.columns,
            "turn": state.turn, "ended": ended, "winner": result,
            "legal": [] if ended else game.get_actions(state), "history": moves, "stats": statistics}


def run(request):
    if request["action"] == "check":
        case = request["case"]
        check = PUBLIC_CHECKS[case][1]
        if case in EVALUATION_CHECKS:
            detail = check(None, import_module("submission.evaluation"))
        else:
            detail = check(import_module("submission.search"), None)
        return {"status": "PASS", "detail": detail} if detail else {"status": "PASS"}
    return game_request(request)


def main():
    try:
        with redirect_stdout(sys.stderr):
            result = run(json.load(sys.stdin))
    except NotImplementedError as error:
        result = {"status": "NOT IMPLEMENTED", "detail": str(error)}
    except AssertionError as error:
        result = {"status": "WRONG ANSWER", "detail": str(error)}
    except Exception as error:
        result = {"status": "RUNTIME ERROR", "detail": f"{type(error).__name__}: {error}"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
