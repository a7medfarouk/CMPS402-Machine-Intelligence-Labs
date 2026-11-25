"""Implement generic search using the game interface in Instructions.md."""

def minvalue(game, state, evaluate, depth, max_player = 0):
    """runs on the opponents turn and returns a utility value"""
    if game.is_terminal(state)[0]:
        return game.is_terminal(state)[1][max_player]
    elif depth == 0:
        return evaluate(game, state, max_player)
    v = float("inf")
    for action in game.get_actions(state):
        v = min(v, maxvalue(game, game.get_successor(state, action), evaluate, depth - 1, max_player))
    return v


def maxvalue(game, state, evaluate, depth, max_player = 0):
    """runs on players turn and returns a utility value"""
    if game.is_terminal(state)[0]:
        return game.is_terminal(state)[1][max_player]
    elif depth == 0:
        return evaluate(game, state, max_player)
    v = float("-inf")
    for action in game.get_actions(state):
        v = max(v, minvalue(game, game.get_successor(state, action), evaluate, depth - 1, max_player))
    return v
    

def minimax(game, state, evaluate, depth, max_player = 0):
    """Return (value, action) at a fixed depth from max_player's perspective."""
    # Ask the game whose turn it is. Check terminal utility before the cutoff.
    if game.is_terminal(state)[0]:
        return game.is_terminal(state)[1][max_player], None
    if depth == 0:
        return evaluate(game, state, max_player), None
    turn = game.get_turn(state)
    action_values = []
    for action in game.get_actions(state):
        if turn == max_player:
            value = minvalue(game, game.get_successor(state, action), evaluate, depth - 1, max_player)
        else:
            value = maxvalue(game, game.get_successor(state, action), evaluate, depth - 1, max_player)
        action_values.append(value)
    if turn == max_player:
        value = max(action_values)
        action_index = action_values.index(value)
        action = game.get_actions(state)[action_index]
        return (value, action)
    else:
        value = min(action_values)
        action_index = action_values.index(value)
        action = game.get_actions(state)[action_index]
        return (value, action)


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
