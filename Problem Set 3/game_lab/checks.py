"""Public unit checks. The search fixtures use opaque string states."""

import math

from .games import Chomp, GAMES, State, WIN, preset_game, replay, zero


class Tree:
    def __init__(self, branches, values, turns):
        self.branches = branches
        self.values = values
        self.turns = turns
        self.visits = []

    def get_actions(self, state):
        return list(self.branches[state])

    def get_successor(self, state, action):
        if action not in self.branches[state]:
            raise ValueError("Action is outside the supplied tree.")
        return action

    def get_turn(self, state):
        return self.turns[state]

    def is_terminal(self, state):
        self.visits.append(state)
        if state in self.values:
            value = self.values[state]
            return True, (value, -value)
        return False, None


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def guarded(game, state, max_player):
    raise AssertionError("A terminal node uses true utility even at the depth cutoff.")


def two_replies():
    return Tree({"root": ("safe", "risky"), "safe": ("a", "b"), "risky": ("c", "d")},
                {"a": 2, "b": 2, "c": -3, "d": 11}, {"root": 0, "safe": 1, "risky": 1})


def minimax(search, evaluation):
    tree = two_replies()
    require(search.minimax(tree, "root", guarded, 2) == (2, "safe"), "A MIN reply uses the worse outcome for MAX.")
    require(search.minimax(tree, "root", guarded, 2, 1) == (-2, "safe"),
            "At a MIN root, minimize the value for the fixed MAX player.")
    require(search.minimax(tree, "c", guarded, 0, 1) == (3, None), "Use the fixed MAX player's utility at a terminal root.")
    require(search.minimax(tree, "root", lambda *args: 7, 0) == (7, None), "At depth zero return the cutoff score and None.")


def pruning(search, evaluation):
    tree = two_replies()
    require(search.alphabeta(tree, "root", guarded, 2) == (2, "safe"), "Alpha-beta must agree with minimax.")
    require("d" not in tree.visits, "The first risky reply is already worse than safe. Skip the remaining reply.")
    tree = Tree({"root": ("left", "right"), "left": ("a", "b"), "right": ("c", "d")},
                {"a": 2, "b": 1, "c": 3, "d": 7}, {"root": 1, "left": 0, "right": 0})
    require(search.alphabeta(tree, "root", guarded, 2) == (2, "left"),
            "At a MIN root, choose the lower value after backing up both MAX children.")
    require("d" not in tree.visits, "At the second MAX child, 3 is already above MIN's upper bound of 2. Skip the remaining reply.")
    require(search.alphabeta(tree, "root", lambda *args: -7, 0) == (-7, None), "Honor the nonterminal cutoff.")
    for player, value in ((0, 2), (1, -2)):
        tree = two_replies()
        tree.values.update(c=2, d=-5)
        require(search.alphabeta(tree, "root", guarded, 2, player) == (value, "safe"),
                "A later branch that only reaches a cutoff bound must not replace the best move.")
        require("d" not in tree.visits, "Prune when alpha and beta meet, including equality.")


def require_ordered_actions(actions, expected, message):
    require(isinstance(actions, (list, tuple)), "order_moves must return a list or tuple of legal actions.")
    require(tuple(actions) == expected, message)


def ordering(search, evaluation):
    scores = {"a": 5, "b": -3, "c": 5}
    evaluate = lambda _, state, player: scores[state]
    tree = Tree({"high": ("b", "c", "a"), "low": ("c", "b", "a")}, {},
                {"high": 0, "low": 1})
    require_ordered_actions(search.order_moves(tree, "high", evaluate), ("c", "a", "b"),
                            "At MAX, high scores go first. Keep legal order on ties.")
    require_ordered_actions(search.order_moves(tree, "low", evaluate), ("b", "c", "a"),
                            "At MIN, low scores go first. Keep legal order on ties.")

    mixed = Tree({"root": ("estimate", "loss", "win")}, {"loss": 4, "win": -6}, {"root": 1})

    def mixed_estimate(game, state, player):
        require(state == "estimate" and player == 1,
                "Estimate only nonterminal successors, from the fixed MAX perspective.")
        return 1

    require_ordered_actions(search.order_moves(mixed, "root", mixed_estimate, 1), ("win", "estimate", "loss"),
                            "Sort actual terminal utilities together with estimates from player 1's perspective.")

    tree = Tree({"root": ("risky", "safe"), "risky": ("rejected", "bad"), "safe": ("steady",),
                 "bad": ("low",), "rejected": ("unused",), "steady": ("moderate",)},
                {"low": -3, "unused": 11, "moderate": 2},
                {"root": 0, "risky": 1, "safe": 1, "bad": 0, "rejected": 0, "steady": 0})
    priorities = {"safe": 5, "risky": -3, "bad": -5, "rejected": 5, "steady": 2}

    def ordering_estimate(game, state, _):
        require(state not in game.values, "Order terminal successors by their true utilities.")
        return priorities[state]

    require(search.alphabeta(tree, "root", ordering_estimate, 3, ordered=True) == (2, "safe"),
            "Ordering cannot change the exact root result.")
    require("unused" not in tree.visits,
            "In ordered mode, try the highest score at MAX and the lowest score at MIN so the unused reply is pruned.")


def expectimax_average(search, evaluation):
    require(search.expectimax(two_replies(), "root", guarded, 2) == (4, "risky"),
            "Risky has mean 4. A chance node averages every reply.")
    tree = Tree({"chance": ("first", "second", "third")}, {"first": -4, "second": 1, "third": 9}, {"chance": 1})
    value, action = search.expectimax(tree, "chance", guarded, 1)
    require(math.isclose(value, 2) and action is None, "At a chance root return the uniform mean and None.")
    tree = Tree({"chance": ("first", "second")}, {"first": -1, "second": -2}, {"chance": 0})
    value, action = search.expectimax(tree, "chance", guarded, 1, 1)
    require(math.isclose(value, 1.5) and action is None,
            "From player 1's perspective the mean is 1.5. Keep fractional values.")


def expectimax_cutoff(search, evaluation):
    tree = two_replies()
    require(search.expectimax(tree, "c", guarded, 0, 1) == (3, None), "Read the fixed player's terminal utility before the cutoff.")
    seen = []

    def evaluate(_, state, max_player):
        seen.append((state, max_player))
        return 5 if state == "safe" else 1

    require(search.expectimax(tree, "root", evaluate, 1) == (5, "safe"), "At the cutoff use the evaluator, with no further replies.")
    require(set(seen) == {("safe", 0), ("risky", 0)}, "Evaluate both cutoff states from the same player's perspective.")


def three_ply_tree():
    return Tree({"root": ("hard", "steady"), "hard": ("c", "d"), "steady": ("e", "f"),
                 "c": ("c1", "c2"), "d": ("d1", "d2"), "f": ("f1", "f2")},
                {"e": 3, "c1": 4, "c2": 7, "d1": 6, "d2": 8, "f1": 1, "f2": 5},
                {"root": 0, "hard": 1, "steady": 1, "c": 0, "d": 0, "f": 0})


def search_depth(algorithm):
    estimates = {"hard": 6, "steady": 3, "c": 0, "d": 9, "f": 6}

    def estimate(game, state, max_player):
        return estimates[state] if max_player == 0 else -estimates[state]

    for player in (0, 1):
        for depth, value, action in ((1, 6, "hard"), (2, 3, "steady"), (3, 7, "hard")):
            tree = three_ply_tree()
            expected = value if player == 0 else -value
            require(algorithm(tree, "root", estimate, depth, player) == (expected, action),
                    f"At depth {depth} with player {player} as MAX, combine terminal utilities and cutoff estimates.")


def minimax_depth(search, _):
    search_depth(search.minimax)


def alphabeta_depth(search, _):
    search_depth(search.alphabeta)
    search_depth(lambda *args: search.alphabeta(*args, ordered=True))


def expectimax_depth(search, _):
    for player, expected, move in ((0, 7.5, "hard"), (1, -4.25, None)):
        value, action = search.expectimax(three_ply_tree(), "root", guarded, 3, player)
        require(math.isclose(value, expected) and action == move,
                f"At depth 3 with player {player} as MAX, alternate decisions and uniform chance at every level.")


def search_boards(search, _):
    four = GAMES["connect-four"]
    finish = replay(four, four.initial, (6, 1, 2, 1, 5, 1, 0))
    bar = GAMES["chomp"]
    hook = replay(bar, bar.initial, ((2, 0), (1, 1), (0, 3)))
    algorithms = (
        ("Minimax", search.minimax),
        ("Alpha-beta", search.alphabeta),
        ("Ordered alpha-beta", lambda *args: search.alphabeta(*args, ordered=True)),
    )
    for name, algorithm in algorithms:
        require(algorithm(four, finish, zero, 2, 1) == (WIN, 1),
                f"{name}: find player 1's immediate vertical Connect Four win.")
        require(algorithm(bar, hook, zero, 3, 0) == (-WIN, (0, 2)),
                f"{name}: at a Chomp MIN root, find the winning bite for the side to move.")


def bounded_score(evaluate, game, state, player):
    result = evaluate(game, state, player)
    require(type(result) in (int, float) and math.isfinite(result) and -WIN < result < WIN,
            "A nonterminal estimate must be a finite number strictly between -1000 and 1000.")
    return result


# Each pair matches disc counts, each player's occupancy in the central three
# columns, and open one- and two-disc line counts. The lone three-disc line
# belongs to the same player and has the same orientation in both boards.
CONNECT_FOUR_THREATS = (
    ("bottom-row", 0, (5, 5, 3, 1, 3, 2, 1, 5, 6, 0), (3, 1, 3, 1, 6, 5, 6, 2, 5, 6)),
    ("elevated horizontal", 1, (5, 5, 1, 3, 6, 6, 4, 3), (1, 3, 0, 3, 5, 0, 4, 1)),
    ("diagonal", 1, (6, 3, 2, 1, 5, 2, 4, 1, 3, 4, 0, 0, 0, 0, 3),
     (5, 6, 0, 0, 4, 5, 0, 3, 3, 0, 2, 2, 6, 4, 3)),
)


def connect_four(evaluation):
    game = GAMES["connect-four"]
    fn = evaluation.evaluate_connect_four
    for label, owner, playable, hanging in CONNECT_FOUR_THREATS:
        for flip in (False, True):
            first, second = (replay(game, game.initial, (6 - move if flip else move for move in history))
                             for history in (playable, hanging))
            require(bounded_score(fn, game, first, owner) > bounded_score(fn, game, second, owner),
                    f"Give the playable {label} threat more weight than the unsupported one.")
            require(bounded_score(fn, game, first, 1 - owner) < bounded_score(fn, game, second, 1 - owner),
                    f"The playable {label} threat should lower the score from the opponent's perspective.")


def connect_four_vertical(evaluation):
    game = GAMES["connect-four"]
    fn = evaluation.evaluate_connect_four
    histories = ((0, 6, 0, 6, 0, 2, 3, 2), (0, 0, 6, 2, 3, 2, 0, 6))
    for flip in (False, True):
        threat, quiet = (replay(game, game.initial, (game.columns - 1 - move if flip else move for move in history))
                         for history in histories)
        require(bounded_score(fn, game, threat, 0) > bounded_score(fn, game, quiet, 0),
                "A playable vertical threat on either side of the board should raise the score for its owner.")
        require(bounded_score(fn, game, threat, 1) < bounded_score(fn, game, quiet, 1),
                "The same vertical threat should lower the score for the opponent.")


def chomp(evaluation):
    fn = evaluation.evaluate_chomp
    for preset in ("start", "wide"):
        game = preset_game("chomp", preset)
        for player in (0, 1):
            bounded_score(fn, game, game.initial, player)
        for turn in (0, 1):
            corner = State((2, 1) + (0,) * (game.rows - 2), turn)
            for player in (0, 1):
                corner_score = bounded_score(fn, game, corner, player)
                for lengths in ((3,), (1, 1, 1)):
                    strip = State(lengths + (0,) * (game.rows - len(lengths)), turn)
                    difference = bounded_score(fn, game, strip, player) - corner_score
                    require(difference > 0 if turn == player else difference < 0,
                            "A strip favors the next player. Check the sign for each MAX player and both strip orientations.")


def chomp_tactics(evaluation):
    game = preset_game("chomp", "wide")
    fn = evaluation.evaluate_chomp
    for turn in (0, 1):
        strip = State((5, 0, 0, 0), turn)
        hook = State((3, 1, 1, 0), turn)
        square = State((2, 2, 0, 0), turn)
        corner = State((2, 1, 0, 0), turn)
        for player in (0, 1):
            direction = 1 if turn == player else -1
            require(direction * (bounded_score(fn, game, strip, player) - bounded_score(fn, game, hook, player)) > 0,
                    "On two five-square shapes, prefer the immediate win for the side to move, even on a longer strip.")
            require(direction * (bounded_score(fn, game, square, player) - bounded_score(fn, game, corner, player)) > 0,
                    "The 2-by-2 square has a bite that avoids immediate loss. The three-square corner has none.")


ENDGAME_CALL_LIMIT = 1400


class CountedChomp(Chomp):
    """Chomp with a successor-call budget for endgame checks."""

    def __init__(self):
        super().__init__(rows=4, columns=7)
        self.successor_calls = 0

    def get_successor(self, state, action):
        self.successor_calls += 1
        require(self.successor_calls <= ENDGAME_CALL_LIMIT,
                f"Exceeded the {ENDGAME_CALL_LIMIT:,} successor-call budget. Try reusing solved positions.")
        return super().get_successor(state, action)


def endgame_solver(search):
    solve = getattr(search, "solve_chomp_endgame", None)
    if solve is None:
        raise NotImplementedError("The optional Chomp endgame solver was not implemented.")
    return solve


def exact_endgame(search, _):
    solve = endgame_solver(search)
    cases = (
        ((1, 0, 0), -WIN, (None,)),
        ((4, 0, 0), WIN, ((0, 1),)),
        ((1, 1, 1, 1), WIN, ((1, 0),)),
        ((2, 1, 0), -WIN, ((0, 1), (1, 0))),
        ((2, 2, 0), WIN, ((1, 1),)),
        ((3, 1, 1), -WIN, ((0, 1), (0, 2), (1, 0), (2, 0))),
        ((4, 2, 1), WIN, ((0, 2),)),
        ((4, 3, 2, 0), WIN, ((1, 2), (2, 0))),
    )
    for board, side_value, actions in cases:
        game = preset_game("chomp", "wide" if len(board) == 4 else "start")
        for turn in (0, 1):
            state = State(board, turn)
            for player in (0, 1):
                value, action = solve(game, state, player)
                expected = side_value if turn == player else -side_value
                require(value == expected and action in actions,
                        f"Rows {board}, player {turn} to move, MAX is {player}: "
                        f"expected value {expected} and an optimal bite, or None at a terminal board.")
    return "32 positions and perspectives passed, including forced losses and tied optimal bites."


def efficient_endgame(search, _):
    solve = endgame_solver(search)
    cases = (
        ((5, 3, 2, 2), 1, WIN, ((3, 0),)),
        ((5, 4, 3, 2), 0, -WIN, ((1, 3), (2, 0))),
    )
    counts = []
    for board, player, expected, actions in cases:
        game = CountedChomp()
        size = sum(board)
        try:
            value, action = solve(game, State(board, 1), player)
        except AssertionError as error:
            raise AssertionError(f"{size}-square board: {error}") from error
        require(value == expected and action in actions,
                f"{size}-square board: return the exact value and an optimal bite for the side to move.")
        counts.append(f"{size} squares: {game.successor_calls:,} / {ENDGAME_CALL_LIMIT:,}")
    return "; ".join(counts) + " successor calls."


EVALUATION_CHECKS = {
    "connect-four": ("Connect Four: supported gaps and perspective", lambda _, evaluation: connect_four(evaluation)),
    "connect-four-vertical": ("Connect Four: vertical threats", lambda _, evaluation: connect_four_vertical(evaluation)),
    "chomp": ("Chomp: strip, corner, and perspective", lambda _, evaluation: chomp(evaluation)),
    "chomp-tactics": ("Chomp: immediate wins and safe bites", lambda _, evaluation: chomp_tactics(evaluation)),
}


CHECKS = {
    "minimax": ("Minimax and base cases", minimax),
    "minimax-depth": ("Minimax at three depth limits", minimax_depth),
    "pruning": ("Alpha-beta and actual pruning", pruning),
    "alphabeta-depth": ("Alpha-beta depth limits in both modes", alphabeta_depth),
    "ordering": ("Stable move ordering and ordered pruning", ordering),
    "search-boards": ("Minimax and both alpha-beta modes on playable boards", search_boards),
    "expectimax-average": ("Expectimax: MAX versus uniform chance", expectimax_average),
    "expectimax-cutoff": ("Expectimax: terminal and cutoff order", expectimax_cutoff),
    "expectimax-depth": ("Expectimax: deeper decisions and chance", expectimax_depth),
    **EVALUATION_CHECKS,
}
BONUS_CHECKS = {
    "bonus-endgame-exact": ("Exact play", exact_endgame),
    "bonus-endgame-budget": ("Successor budget", efficient_endgame),
}
PUBLIC_CHECKS = {**CHECKS, **BONUS_CHECKS}
