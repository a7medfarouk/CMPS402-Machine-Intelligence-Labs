"""Implement generic BFS, DFS, UCS, greedy, and A*; shared helpers are allowed."""

from campus.contracts import Node, Problem, reconstruct
from collections import deque
import heapq

def BreadthFirstSearch(problem : Problem, initial_state):
    node = Node(initial_state)
    if problem.is_goal(node.state):
        return reconstruct(node)

    frontier = deque([node])
    frontier_states = {node.state}
    explored = set()

    while frontier:
        node = frontier.popleft()
        frontier_states.discard(node.state)
        explored.add(node.state)

        for action in problem.get_actions(node.state):
            child_state = problem.get_successor(node.state, action)
            if not (child_state in explored or child_state in frontier_states):
                child = Node(child_state, node.cost + problem.get_cost(node.state, action), node, action)
                if problem.is_goal(child.state):
                    return reconstruct(child)
                frontier.append(child)
                frontier_states.add(child.state)

    return None


def DepthFirstSearch(problem : Problem, initial_state):
    node = Node(initial_state)
    if problem.is_goal(node.state):
        return reconstruct(node)

    frontier = deque([node])
    frontier_states = {node.state}
    explored = set()

    while frontier:
        node = frontier.pop()
        frontier_states.discard(node.state)
        if problem.is_goal(node.state):
            return reconstruct(node)
        explored.add(node.state)

        for action in problem.get_actions(node.state):
            child_state = problem.get_successor(node.state, action)
            if not (child_state in explored or child_state in frontier_states):
                child = Node(child_state, node.cost + problem.get_cost(node.state, action), node, action)
                frontier.append(child)
                frontier_states.add(child.state)

    return None


def UniformCostSearch(problem, initial_state):
    node = Node(initial_state)                      
    order = 0                                       
    frontier = [(node.cost, order, node)]           
    in_frontier = {node.state: node}                
    explored = set()                                

    while in_frontier:                              
        while (node := heapq.heappop(frontier)[2]).state in explored:
            pass                                    
        del in_frontier[node.state]
        if problem.is_goal(node.state):            
            return reconstruct(node)
        explored.add(node.state)                    

        for action in problem.get_actions(node.state):          
            child = Node(                                       
                problem.get_successor(node.state, action),
                node.cost + problem.get_cost(node.state, action),
                node,
                action,
            )
            if child.state not in explored and child.state not in in_frontier:
                order += 1
                heapq.heappush(frontier, (child.cost, order, child))
                in_frontier[child.state] = child
            elif child.state in in_frontier and in_frontier[child.state].cost > child.cost:
                order += 1                                      
                heapq.heappush(frontier, (child.cost, order, child))
                in_frontier[child.state] = child
    return None


def AStarSearch(problem, initial_state, heuristic):
    node = Node(initial_state)                      
    order = 0
    node_heuristic = heuristic(problem, node.state)                                       
    frontier = [(node.cost + node_heuristic, order, node)]           
    in_frontier = {node.state: node}                
    explored = set()                                

    while in_frontier:                              
        while (node := heapq.heappop(frontier)[2]).state in explored:
            pass                                    
        del in_frontier[node.state]
        if problem.is_goal(node.state):            
            return reconstruct(node)
        explored.add(node.state)                    

        for action in problem.get_actions(node.state):          
            child = Node(                                       
                problem.get_successor(node.state, action),
                node.cost + problem.get_cost(node.state, action),
                node,
                action,
            )
            if child.state not in explored and child.state not in in_frontier:
                order += 1
                child_heuristic = heuristic(problem, child.state)
                heapq.heappush(frontier, (child.cost + child_heuristic, order, child))
                in_frontier[child.state] = child
            elif child.state in in_frontier and in_frontier[child.state].cost > child.cost:
                order += 1
                child_heuristic = heuristic(problem, child.state)
                heapq.heappush(frontier, (child.cost + child_heuristic, order, child))
                in_frontier[child.state] = child

    return None


def BestFirstSearch(problem, initial_state, heuristic):
    node = Node(initial_state)                      
    order = 0                                       
    frontier = [(node.cost, order, node)]           
    in_frontier = {node.state: node}                
    explored = set()                                

    while in_frontier:                              
        while (node := heapq.heappop(frontier)[2]).state in explored:
            pass                                    
        del in_frontier[node.state]
        if problem.is_goal(node.state):            
            return reconstruct(node)
        explored.add(node.state)                    

        for action in problem.get_actions(node.state):          
            child = Node(                                       
                problem.get_successor(node.state, action),
                heuristic(problem, problem.get_successor(node.state, action)),
                node,
                action,
            )
            if child.state not in explored and child.state not in in_frontier:
                order += 1
                heapq.heappush(frontier, (child.cost, order, child))
                in_frontier[child.state] = child
            elif child.state in in_frontier and in_frontier[child.state].cost > child.cost:
                order += 1                                      
                heapq.heappush(frontier, (child.cost, order, child))
                in_frontier[child.state] = child
    return None


def solve(problem, algorithm="astar", heuristic=None):
    """Supplied dispatcher; implement the five entry points above."""
    functions = {"bfs": BreadthFirstSearch, "dfs": DepthFirstSearch, "ucs": UniformCostSearch, "greedy": BestFirstSearch, "astar": AStarSearch}
    if algorithm not in functions:
        raise ValueError(algorithm)
    initial_state = problem.get_initial_state()
    if algorithm in {"greedy", "astar"}:
        estimate = heuristic or (lambda state: 0)
        return functions[algorithm](problem, initial_state, lambda current_problem, state: estimate(state))
    return functions[algorithm](problem, initial_state)
