"""Score nonterminal positions from a fixed MAX perspective."""


def evaluate_connect_four(game, state, max_player):
    """Use Connect Four features to return a finite score between -1000 and 1000."""
    # state.board contains six rows of seven cells (None, 0 or 1).
    # Each line in game.lines is a tuple of four (row, column) coordinates.
    raise NotImplementedError("Implement the Connect Four evaluator.")


def evaluate_chomp(game, state, max_player):
    """Use the bar shape and side to move to score Chomp."""
    # state.board holds one remaining length per row (three or four rows).
    # Each action is a (row, column) pair. game.get_turn(state) identifies who moves next.
    raise NotImplementedError("Implement the Chomp evaluator.")
