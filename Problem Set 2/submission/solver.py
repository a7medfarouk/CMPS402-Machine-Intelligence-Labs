"""Implement the generic CSP algorithms, without inspecting timetable records."""

from typing import Dict, List, Set, Tuple

from scheduler.contracts import BinaryConstraint, Problem, UnaryConstraint

# scheduler/contracts.py supplies Problem.variables, .domains and .constraints.
# problem.is_complete(assignment) checks for all variables; it does NOT check validity.
# problem.satisfies_constraints(assignment) expects a complete assignment.
# A unary condition takes one value. A binary condition takes two in
# constraint.variables order; constraint.is_satisfied({name: value, ...}) handles that order.
# constraint.get_other(variable) returns the other endpoint; call it only on an endpoint.
#
# In MRV, LCV and forward checking, domains holds only UNASSIGNED variables.
# A missing key means assigned. A present key with set() means unassigned with no choices.


def one_consistency(problem: Problem):
    """Filter unary domains, remove unary constraints and return whether all domains survive."""
    retained_constraints: List = []
    for constraint in problem.constraints:
        if isinstance(constraint, BinaryConstraint):
            retained_constraints.append(constraint)
        elif isinstance(constraint, UnaryConstraint):
            domain = problem.domains[constraint.variable]
            for value in domain.copy():
                if not constraint.is_satisfied({constraint.variable: value}):
                    domain.remove(value)
    problem.constraints = retained_constraints     
    return all(problem.domains[variable] for variable in problem.variables)

def minimum_remaining_values(problem: Problem, domains: Dict[str, Set]) -> str:
    """Choose the smallest current domain, including size zero; use declared order for ties."""
    for variable in problem.variables:
        if variable not in domains:
            continue
        else:
            min_domain_variable: str = variable
            break
    for variable in problem.variables:
        if variable not in domains:
            continue     
        if len(domains[variable]) < len(domains[min_domain_variable]):
            min_domain_variable = variable
    return min_domain_variable


def least_constraining_values(problem: Problem, variable: str, domains: Dict[str, Set]) -> List:
    """Order values by distinct neighbor values removed; break ties by ascending value."""
    # LCV only scores the choices; it must not change the supplied domains.
    lcv_order: list[tuple[str, int]] = []
    for value in domains[variable]:
        order: int = 0
        for constraint in problem.constraints:
            if isinstance(constraint, BinaryConstraint) and variable in constraint.variables:
                neighbor: str = constraint.get_other(variable)
                if neighbor in domains:
                    for neighbor_value in domains[neighbor]:
                        valid: bool = True
                        for constr in problem.constraints:
                            if isinstance(constr, BinaryConstraint) and variable in constr.variables and neighbor in constr.variables:
                                if not constr.is_satisfied({variable: value, neighbor: neighbor_value}):
                                    valid = False
                                    break
                        if valid:
                            order += 1
        lcv_order.append((value, order))
    lcv_order.sort(key= lambda pair: (-pair[1],pair[0]))           
    return [value for value,_ in lcv_order]


def forward_checking(problem, assigned_variable, assigned_value, domains):
    """Filter all direct unassigned neighbors and report whether domains survive."""
    # assigned_variable has already been removed from domains. Apply all relevant
    # predicates for each neighbor. Keep size-zero entries; do not propagate from neighbors.
    raise NotImplementedError("Implement forward checking.")


def solve(problem):
    """Use the four helpers; return a valid complete assignment or None."""
    # Before forward checking, add the value to the branch assignment and remove
    # that variable from the branch domains. Failed branches must not affect siblings.
    # {} is a valid solution to a problem with no variables, not a failure signal.
    raise NotImplementedError("Implement backtracking with the required helpers.")


def arc_consistency(problem):
    """Run AC-3 on a binary CSP after unary filtering and report whether all domains survive."""
    # Work on problem.domains. Each constrained pair has two directed arcs.
    # A supporting neighbor value must satisfy all constraints on the pair together.
    # BinaryConstraint.is_satisfied handles the endpoint order of each rule.
    raise NotImplementedError("Implement standalone AC-3.")
