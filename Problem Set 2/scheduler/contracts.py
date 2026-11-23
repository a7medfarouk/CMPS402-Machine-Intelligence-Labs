"""Generic unary/binary CSP objects and the advisor result contract."""

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from enum import StrEnum


type Assignment = dict[str, Hashable]
type Schedule = dict[str, str]


@dataclass(frozen=True)
class UnaryConstraint:
    variable: str
    condition: Callable

    def is_satisfied(self, assignment):
        return self.variable in assignment and self.condition(assignment[self.variable])


@dataclass(frozen=True)
class BinaryConstraint:
    variables: tuple[str, str]
    condition: Callable

    def is_satisfied(self, assignment):
        first, second = self.variables
        return first in assignment and second in assignment and self.condition(assignment[first], assignment[second])

    def get_other(self, variable):
        first, second = self.variables
        if variable == first:
            return second
        if variable == second:
            return first
        raise ValueError("Variable is not an endpoint of this constraint.")


@dataclass
class Problem:
    variables: tuple[str, ...]
    domains: dict[str, set]
    constraints: list[UnaryConstraint | BinaryConstraint]

    def is_complete(self, assignment):
        return all(variable in assignment for variable in self.variables)

    def satisfies_constraints(self, assignment):
        return all(constraint.is_satisfied(assignment) for constraint in self.constraints)


class SolveStatus(StrEnum):
    SAT = "SAT"
    UNSAT = "UNSAT"
    LIMIT = "LIMIT"


class Verdict(StrEnum):
    SCHEDULE = "SCHEDULE FOUND"
    BASE_INFEASIBLE = "BASE INFEASIBLE"
    POSSIBLE = "POSSIBLE"
    IMPOSSIBLE = "IMPOSSIBLE"
    NOT_UNAVOIDABLE = "NOT UNAVOIDABLE"
    UNAVOIDABLE = "UNAVOIDABLE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class SolveResult:
    status: SolveStatus
    schedule: Schedule | None = None


@dataclass(frozen=True)
class Advice:
    verdict: Verdict
    schedule: Schedule | None = None
