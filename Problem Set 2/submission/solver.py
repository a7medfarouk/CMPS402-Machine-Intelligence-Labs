"""Implement the generic CSP algorithms, without inspecting timetable records."""

from scheduler.contracts import BinaryConstraint, UnaryConstraint

# scheduler/contracts.py supplies Problem.variables, .domains and .constraints.
# problem.is_complete(assignment) checks for all variables; it does NOT check validity.
# problem.satisfies_constraints(assignment) expects a complete assignment.
# A unary condition takes one value. A binary condition takes two in
# constraint.variables order; constraint.is_satisfied({name: value, ...}) handles that order.
# constraint.get_other(variable) returns the other endpoint; call it only on an endpoint.
#
# In MRV, LCV and forward checking, domains holds only UNASSIGNED variables.
# A missing key means assigned. A present key with set() means unassigned with no choices.


def one_consistency(problem):
    """Filter unary domains, remove unary constraints and return whether all domains survive."""
    # Build the retained constraint list separately; do not delete items during iteration.
    raise NotImplementedError("Implement node consistency.")


def minimum_remaining_values(problem, domains):
    """Choose the smallest current domain, including size zero; use declared order for ties."""
    raise NotImplementedError("Implement MRV.")


def least_constraining_values(problem, variable, domains):
    """Order values by distinct neighbor values removed; break ties by ascending value."""
    # LCV only scores the choices; it must not change the supplied domains.
    raise NotImplementedError("Implement LCV.")


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
