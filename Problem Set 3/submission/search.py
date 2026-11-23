"""Implement generic search using the game interface in Instructions.md."""


def minimax(game, state, evaluate, depth, max_player=0):
    """Return (value, action) at a fixed depth from max_player's perspective."""
    # Ask the game whose turn it is. Check terminal utility before the cutoff.
    raise NotImplementedError("Implement depth-limited minimax.")


def alphabeta(game, state, evaluate, depth, max_player=0, *, ordered=False):
    """Return (value, action); use order_moves when ordered and more than one move remains."""
    # A pruned child's returned bound need not equal its exact minimax value.
    raise NotImplementedError("Implement alpha-beta pruning.")


def order_moves(game, state, evaluate, max_player=0):
    """Return a list or tuple of legal actions by successor score, with stable ties."""
    # Score terminal successors by utility. At a MIN node, lower scores go first.
    raise NotImplementedError("Implement evaluator-based move ordering.")


def expectimax(game, state, evaluate, depth, max_player=0):
    """Return (value, action) for a MAX decision and uniformly random opposition."""
    # Unit tests call this function on tree fixtures. A chance root has no action.
    raise NotImplementedError("Implement standalone expectimax.")


def solve_chomp_endgame(game, state, max_player=0):
    """Optional bonus. Return the exact Chomp utility and an optimal move."""
    raise NotImplementedError("The optional Chomp endgame solver was not implemented.")
