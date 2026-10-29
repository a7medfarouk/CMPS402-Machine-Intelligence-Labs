"""Design an admissible and consistent pickup-aware lower bound."""
from campus.contracts import Problem, WorldState
from campus.maps import MapSpec

def heuristic(problem, state):
    """Use problem.describe(state) and problem.map, not your model's state fields or tuple layout."""
    map : MapSpec = problem.map
    situation : WorldState = problem.describe(state)
    if (situation.has_key or map.pickup is None):
        x1 = situation.row
        y1 = situation.column
        x2, y2 = map.goal
        return manhatten_dist(x1, x2, y1, y2)
    else:
        x1 = situation.row
        y1 = situation.column
        x2, y2 = map.pickup
        x3,y3 = map.goal
        
        state_key_estimate = manhatten_dist(x1, x2, y1, y2)
        
        key_goal_estimate = manhatten_dist(x2,x3,y2,y3)
        
        return state_key_estimate + key_goal_estimate
    
def manhatten_dist(x1, x2, y1, y2):
    
    return abs(y2-y1) + abs(x2-x1)