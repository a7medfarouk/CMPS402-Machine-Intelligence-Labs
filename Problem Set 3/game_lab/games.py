"""Immutable games and reachable starting positions."""

from dataclasses import dataclass

WIN = 1000


@dataclass(frozen=True)
class State:
    board: tuple
    turn: int = 0


def outcome(winner):
    if winner is None:
        return True, (0, 0)
    return True, (WIN, -WIN) if winner == 0 else (-WIN, WIN)


class Game:
    @staticmethod
    def get_turn(state):
        return state.turn


class ConnectFour(Game):
    rows = 6
    columns = 7
    initial = State(((None,) * columns,) * rows)
    lines = tuple(
        tuple((r + step * dr, c + step * dc) for step in range(4))
        for r in range(6) for c in range(7)
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1))
        if 0 <= r + 3 * dr < 6 and 0 <= c + 3 * dc < 7
    )

    def windows(self, state):
        for line in self.lines:
            yield tuple(state.board[row][col] for row, col in line)

    def is_terminal(self, state):
        for first, second, third, fourth in self.windows(state):
            if first is not None and first == second == third == fourth:
                return outcome(first)
        return outcome(None) if None not in state.board[0] else (False, None)

    @staticmethod
    def get_actions(state):
        return [column for column, top in enumerate(state.board[0]) if top is None]

    @staticmethod
    def get_successor(state, action):
        if type(action) is not int or not 0 <= action < len(state.board[0]):
            raise ValueError("Choose a column on the board.")
        for row in reversed(range(len(state.board))):
            if state.board[row][action] is None:
                changed = list(state.board[row])
                changed[action] = state.turn
                return State(state.board[:row] + (tuple(changed),) + state.board[row + 1:], 1 - state.turn)
        raise ValueError("That column is full.")


class Chomp(Game):
    def __init__(self, rows=3, columns=4):
        self.rows = rows
        self.columns = columns
        self.initial = State((columns,) * rows)

    @staticmethod
    def is_terminal(state):
        return outcome(1 - state.turn) if sum(state.board) == 1 else (False, None)

    @staticmethod
    def get_actions(state):
        return [(row, col) for row, length in enumerate(state.board)
                for col in range(length) if (row, col) != (0, 0)]

    @staticmethod
    def get_successor(state, action):
        if not isinstance(action, (tuple, list)) or len(action) != 2:
            raise ValueError("A Chomp bite needs a row and column.")
        row, col = action
        if (type(row) is not int or type(col) is not int or (row, col) == (0, 0)
                or not 0 <= row < len(state.board) or not 0 <= col < state.board[row]):
            raise ValueError("Choose a remaining square other than poison.")
        board = tuple(min(length, col) if index >= row else length for index, length in enumerate(state.board))
        return State(board, 1 - state.turn)


GAMES = {"connect-four": ConnectFour(), "chomp": Chomp()}
WIDE_CHOMP = Chomp(rows=4, columns=7)
PRESETS = {
    "connect-four": {"start": (), "ordering": (3, 2, 3, 2, 4, 1)},
    "chomp": {"start": (), "wide": (), "row": ((1, 0), (0, 3)), "corner": ((1, 1), (2, 0), (0, 2))},
}


def preset_game(name, preset):
    return WIDE_CHOMP if (name, preset) == ("chomp", "wide") else GAMES[name]


def replay(game, state, moves):
    for move in moves:
        if game.is_terminal(state)[0] or move not in game.get_actions(state):
            raise ValueError("The move is illegal on this board.")
        state = game.get_successor(state, move)
    return state


def zero(game, state, max_player):
    return 0


def baseline(game, state):
    """Rules-based opponent for exploring the app before writing search code."""
    actions = game.get_actions(state)
    successors = []
    for action in actions:
        successor = game.get_successor(state, action)
        ended, values = game.is_terminal(successor)
        if ended and values[state.turn] == WIN:
            return WIN, action
        successors.append((action, successor))
    if isinstance(game, ConnectFour):
        opponent = State(state.board, 1 - state.turn)
        for action in actions:
            ended, values = game.is_terminal(game.get_successor(opponent, action))
            if ended and values[opponent.turn] == WIN:
                return 0, action
        return 0, min(actions, key=lambda action: abs(3 - action))
    def chomp_priority(candidate):
        _, successor = candidate
        gives_away_win = any(game.is_terminal(game.get_successor(successor, reply))[0]
                            for reply in game.get_actions(successor))
        return not gives_away_win, sum(successor.board)

    return 0, max(successors, key=chomp_priority)[0]
