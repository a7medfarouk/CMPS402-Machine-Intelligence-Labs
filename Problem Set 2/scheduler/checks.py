"""Published micro-checks, with no reference model or solver."""

from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from .catalogue import Catalogue, Link, Meeting, Query, Request, Section
from .contracts import Advice, BinaryConstraint, Problem, SolveResult, SolveStatus, UnaryConstraint, Verdict
from .execution import load_part, satisfies_query


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def model_shape(model, catalogue, requests):
    request = requests["single-course"]
    expected = {component: {item.identifier for item in catalogue.sections[component]} for component in request.components}
    actual = model.build_domains(catalogue, request)
    require(actual == expected, "Return one set of section ID strings per requested component.")
    actual[request.components[0]].clear()
    require(model.build_domains(catalogue, request) == expected, "Build a new set for each domain on every call.")
    require(model.build_domains(catalogue, requests["empty"]) == {}, "No requested courses means no domain keys.")
    no_sections = replace(catalogue, sections={**catalogue.sections, request.components[0]: ()})
    require(model.build_domains(no_sections, request) == {**expected, request.components[0]: set()},
            "A requested component with no sections still needs an empty domain.")


def with_rules(model, catalogue, request):
    domains = {component: {section.identifier for section in catalogue.sections[component]}
               for component in request.components}
    problem = Problem(request.components, deepcopy(domains), [])
    require(model.add_constraints(problem, catalogue, request) is None,
            "Append to problem.constraints and return None.")
    require(problem.variables == request.components and problem.domains == domains,
            "Adding constraints must not change variables or filter initial domains.")
    require(isinstance(problem.constraints, list) and all(isinstance(rule, (UnaryConstraint, BinaryConstraint))
            for rule in problem.constraints), "Add supplied constraint objects, not boolean results.")
    return problem


def model_links(model, catalogue, requests):
    linked = requests["linked"]
    problem = with_rules(model, catalogue, linked)
    for lecture, tutorial, valid in (("L1", "T1", True), ("L1", "T2", False), ("L2", "T2", True)):
        assignment = {"MTHS102.lecture": lecture, "MTHS102.tutorial": tutorial}
        require(problem.satisfies_constraints(assignment) == valid,
                f"Check the MTHS102 pair {lecture}/{tutorial}; this link is stored tutorial-first.")
    empty = replace(catalogue, links=(replace(catalogue.links[0], allowed=frozenset()),))
    pair = {"MTHS102.lecture": "L1", "MTHS102.tutorial": "T1"}
    require(not with_rules(model, empty, linked).satisfies_constraints(pair),
            "An explicit empty allow-list rejects every pairing.")
    absent = replace(catalogue, links=())
    require(with_rules(model, absent, linked).satisfies_constraints({**pair, "MTHS102.tutorial": "T2"}),
            "Without a link, mismatched section numbers are allowed if times fit.")
    single = Request(("MTHS102.lecture",))
    require(with_rules(model, catalogue, single).satisfies_constraints({"MTHS102.lecture": "L1"}),
            "Ignore links when the other endpoint is outside the request.")
    free = with_rules(model, catalogue, requests["single-course"])
    require(free.satisfies_constraints({"CMPS402.lecture": "L1", "CMPS402.tutorial": "T4"}),
            "CMPS402 L1/T4 has no linking restriction and no clash.")
    circuits = with_rules(model, catalogue, Request(("EECS102.lecture", "EECS102.tutorial")))
    require(circuits.satisfies_constraints({"EECS102.lecture": "L1", "EECS102.tutorial": "T2"}),
            "EECS102 lecture and tutorial section numbers need not match.")


def model_times(model, catalogue, requests):
    request = Request(("CMPS202.lecture", "CMPS202.tutorial"))
    problem = with_rules(model, catalogue, request)
    require(problem.satisfies_constraints({"CMPS202.lecture": "L1", "CMPS202.tutorial": "T1"}),
            "An end time equal to the next start time is not an overlap.")
    free = with_rules(model, catalogue, requests["single-course"])
    require(not free.satisfies_constraints({"CMPS402.lecture": "L2", "CMPS402.tutorial": "T3"}),
            "Unlinked sections still cannot overlap, even within one course.")
    identical = replace(catalogue, sections={**catalogue.sections,
                        "CMPS202.tutorial": (Section("T1", catalogue.sections["CMPS202.lecture"][0].meeting),)})
    require(not with_rules(model, identical, request).satisfies_constraints(
            {"CMPS202.lecture": "L1", "CMPS202.tutorial": "T1"}),
            "Two selected components with identical time slots clash.")


def model_availability(model, catalogue, requests):
    request = replace(requests["single-course"], unavailable=(Meeting("Tue", 600, 630),))
    problem = with_rules(model, catalogue, request)
    require(not problem.satisfies_constraints({"CMPS402.lecture": "L2", "CMPS402.tutorial": "T4"}),
            "Reject even a partial overlap with a blocked interval.")
    require(problem.satisfies_constraints({"CMPS402.lecture": "L1", "CMPS402.tutorial": "T4"}),
            "An unavailable interval does not block the same time on a different day.")
    request = replace(request, unavailable=(Meeting("Mon", 660, 720),))
    require(with_rules(model, catalogue, request).satisfies_constraints(
            {"CMPS402.lecture": "L1", "CMPS402.tutorial": "T4"}),
            "A section ending when a blocked interval begins is allowed.")
    single = Request(("CMPS402.lecture",), (Meeting("Mon", 570, 600),))
    require(not with_rules(model, catalogue, single).satisfies_constraints({"CMPS402.lecture": "L1"}),
            "Unavailable times must still constrain a request with only one variable.")


def one_consistency(solver, *_):
    unary = [UnaryConstraint("first", lambda value: value >= 2), UnaryConstraint("first", lambda value: value != 3)]
    binary = BinaryConstraint(("first", "second"), lambda first, second: first != second)
    problem = Problem(("first", "second"), {"first": {1, 2, 3}, "second": {2, 3}}, [*unary, binary])
    require(solver.one_consistency(problem) is True, "A remaining unary-consistent value should survive.")
    require(problem.domains == {"first": {2}, "second": {2, 3}} and problem.constraints == [binary],
            "Apply all unary restrictions and leave the binary constraint in place.")
    problem = Problem(("empty",), {"empty": set()}, [])
    require(solver.one_consistency(problem) is False, "An already empty domain must fail node consistency.")


def mrv(solver, *_):
    problem = Problem(("z", "b", "a"), {"z": {0}, "b": {0, 1, 2}, "a": {0, 1, 2}}, [])
    require(solver.minimum_remaining_values(problem, {"a": {0}, "b": {0}}) == "b",
            "Use current unassigned domains; resolve equal sizes by problem.variables order.")
    require(solver.minimum_remaining_values(problem, {"a": set(), "b": {0}}) == "a",
            "A present key with an empty set is unassigned with zero choices, not an assigned variable.")


def lcv(solver, *_):
    domains = {"choice": {1, 2, 3}, "neighbor": {1, 2, 3}}
    problem = Problem(tuple(domains), deepcopy(domains), [
        BinaryConstraint(("choice", "neighbor"), lambda choice, neighbor: (choice, neighbor) not in {(1, 1), (2, 2)}),
        BinaryConstraint(("neighbor", "choice"), lambda neighbor, choice: (choice, neighbor) != (1, 1)),
    ])
    require(list(solver.least_constraining_values(problem, "choice", domains)) == [3, 1, 2],
            "Count each eliminated neighbor value once, even if two constraints reject it.")
    require(domains == problem.domains == {"choice": {1, 2, 3}, "neighbor": {1, 2, 3}},
            "LCV must not change the domains it receives.")


def forward(solver, *_):
    problem = Problem(("x", "y", "z", "other", "prior"), {}, [
        BinaryConstraint(("y", "x"), lambda neighbor, chosen: neighbor > chosen),
        BinaryConstraint(("x", "y"), lambda chosen, neighbor: chosen != 1 or neighbor != 3),
        BinaryConstraint(("x", "z"), lambda chosen, neighbor: chosen == neighbor),
        BinaryConstraint(("y", "other"), lambda first, second: first != second),
        BinaryConstraint(("x", "prior"), lambda first, second: False),
    ])
    domains = {"y": {1, 2, 3}, "z": {2}, "other": {2}}
    require(solver.forward_checking(problem, "x", 1, domains) is False,
            "A wiped-out unassigned domain means this branch fails.")
    require(domains == {"y": {2}, "z": set(), "other": {2}},
            "Filter every direct neighbor with all its constraints, and leave non-neighbors alone.")
    domains = {"y": {1, 2, 3}, "z": {1, 2}, "other": {2}}
    require(solver.forward_checking(problem, "x", 1, domains) is True
            and domains == {"y": {2}, "z": {1}, "other": {2}},
            "Return True when every domain survives; a missing key such as prior is already assigned.")


def triangle(colors):
    variables = ("a", "b", "c")
    return Problem(variables, {name: set(colors) for name in variables}, [
        BinaryConstraint(edge, lambda first, second: first != second)
        for edge in (("a", "b"), ("b", "c"), ("c", "a"))
    ])


def arc_result(solver, problem, expected_domains):
    variables = problem.variables
    constraints = problem.constraints.copy()
    result = solver.arc_consistency(problem)
    survived = expected_domains is not None
    require(result is survived, f"Return {survived} for this set of domains.")
    require(problem.variables == variables and problem.constraints == constraints,
            "Leave the variables and binary constraints unchanged.")
    require(set(problem.domains) == set(variables), "Keep a domain key for each variable.")
    if survived:
        require(problem.domains == expected_domains, f"Expected the pruned domains {expected_domains!r}.")
    else:
        require(any(not values for values in problem.domains.values()), "Report failure with an empty domain.")


def arc_propagation(solver, *_):
    domains = {"x": {1, 2}, "y": {1, 2}, "z": {2}, "independent": {1, 2}}
    edges = [BinaryConstraint(pair, lambda left, right: left == right)
             for pair in (("x", "y"), ("y", "z"))]
    expected = {**domains, "x": {2}, "y": {2}}
    for order in (edges, list(reversed(edges))):
        arc_result(solver, Problem(tuple(domains), deepcopy(domains), order.copy()), expected)


def arc_directions(solver, *_):
    domains = {"x": {1, 2, 3}, "y": {1, 2, 3}}
    arc_result(solver, Problem(tuple(domains), domains, [
        BinaryConstraint(("x", "y"), lambda x, y: x < y),
    ]), {"x": {1, 2}, "y": {2, 3}})


def arc_wipeout(solver, *_):
    arc_result(solver, Problem(("x", "y"), {"x": {3}, "y": {1, 2}}, [
        BinaryConstraint(("x", "y"), lambda x, y: x < y),
    ]), None)
    arc_result(solver, Problem(("orphan",), {"orphan": set()}, []), None)
    arc_result(solver, Problem(("a", "b"), {"a": {1, 2}, "b": {1, 2}}, [
        BinaryConstraint(("a", "b"), lambda a, b: a == b),
        BinaryConstraint(("b", "a"), lambda b, a: b != a),
    ]), None)


def arc_local(solver, *_):
    arc_result(solver, triangle({1, 2}), {"a": {1, 2}, "b": {1, 2}, "c": {1, 2}})
    arc_result(solver, Problem((), {}, []), {})


def solver_general(solver, *_):
    require(solver.solve(Problem((), {}, [])) == {}, "Zero variables has the empty solution, not None.")
    require(solver.solve(triangle({1, 2})) is None, "Three pairwise-different variables cannot use only two values.")
    problem = triangle({1, 2, 3})
    schedule = solver.solve(problem)
    require(isinstance(schedule, dict) and set(schedule) == set(problem.variables)
            and all(value in {1, 2, 3} for value in schedule.values()) and problem.satisfies_constraints(schedule),
            "Return a complete consistent assignment on a generic CSP.")


def restoration_problem():
    problem = triangle({0, 1, 2})
    problem.variables = ("gate", *problem.variables, "extra")
    problem.domains.update(gate={0, 1}, extra={0, 1, 2, 3, 4})
    problem.constraints.extend(
        BinaryConstraint(("gate", name), lambda gate, color: gate == 1 or color != 2)
        for name in ("a", "b", "c")
    )
    problem.constraints.append(BinaryConstraint(("gate", "extra"), lambda gate, value: gate == 0 or value == 0))
    return problem


def solver_restoration(solver, *_):
    problem = restoration_problem()
    before = deepcopy(problem.domains)
    result = solver.solve(problem)
    require(isinstance(result, dict) and set(result) == set(problem.variables) and result["gate"] == 1
            and all(value in before[name] for name, value in result.items()) and problem.satisfies_constraints(result),
            "The first branch fails. Restore every value needed by its sibling branch.")


def solver_uses_helpers(solver, *_):
    names = ("one_consistency", "minimum_remaining_values", "least_constraining_values", "forward_checking")
    original = solver.forward_checking

    def checked_forward(problem, assigned_variable, assigned_value, domains):
        require(assigned_variable not in domains, "Remove the assigned variable before forward checking.")
        return original(problem, assigned_variable, assigned_value, domains)

    from contextlib import ExitStack
    with ExitStack() as stack:
        calls = {name: stack.enter_context(patch.object(
            solver, name, wraps=checked_forward if name == "forward_checking" else getattr(solver, name)
        )) for name in names}
        solver.solve(restoration_problem())
    require(all(mock.called for mock in calls.values()), "solve must use all four required helpers.")


def fixture_callback(schedules, limit_at=None):
    calls = []

    def solve_request(allowed):
        calls.append({name: frozenset(values) for name, values in allowed.items()})
        if len(calls) == limit_at:
            return SolveResult(SolveStatus.LIMIT)
        for schedule in schedules:
            if all(schedule.get(name) in values for name, values in allowed.items()):
                return SolveResult(SolveStatus.SAT, schedule.copy())
        return SolveResult(SolveStatus.UNSAT)

    return solve_request, calls


def advice_case(advisor, catalogue, request, query, schedules, verdict, limit_at=None):
    callback, calls = fixture_callback(schedules, limit_at)
    advice = advisor.answer_query(catalogue, request, query, callback)
    require(isinstance(advice, Advice) and advice.verdict == verdict, f"Expected {verdict} for {query.kind}.")
    require(calls and calls[0] == {}, "Establish base feasibility before applying a hypothetical restriction.")
    if verdict in {Verdict.POSSIBLE, Verdict.NOT_UNAVOIDABLE}:
        require(advice.schedule in schedules and satisfies_query(catalogue, advice.schedule, query),
                "Return a witness that satisfies the base rules and answers the actual question.")
    else:
        require(advice.schedule is None, "Do not attach a witness to this verdict.")
    if limit_at is not None or not schedules:
        require(len(calls) == (limit_at or 1), "Stop after a limit or a proven infeasible base.")
    return advice


ALTERNATIVES = [{"CMPS402.lecture": lecture, "CMPS402.tutorial": tutorial}
                for lecture in ("L1", "L2") for tutorial in ("T1", "T2", "T3", "T4")
                if (lecture, tutorial) != ("L2", "T3")]
FORCED = [{"CMPS402.lecture": "L2", "CMPS402.tutorial": tutorial, "MTHS102.lecture": "L1", "MTHS102.tutorial": "T1"}
          for tutorial in ("T1", "T2", "T4")]


def advice_take(advisor, catalogue, requests):
    advice_case(advisor, catalogue, requests["single-course"], Query("take", "CMPS402.tutorial", "T4"), ALTERNATIVES, Verdict.POSSIBLE)
    advice_case(advisor, catalogue, requests["forced"], Query("take", "CMPS402.lecture", "L1"), FORCED, Verdict.IMPOSSIBLE)


def advice_day(advisor, catalogue, requests):
    query = Query("avoid-day", day="Tue")
    advice_case(advisor, catalogue, requests["single-course"], query, ALTERNATIVES, Verdict.POSSIBLE)
    advice_case(advisor, catalogue, requests["forced"], query, FORCED, Verdict.IMPOSSIBLE)
    advice_case(advisor, catalogue, requests["empty"], query, [{}], Verdict.POSSIBLE)


def advice_unavoidable(advisor, catalogue, requests):
    query = Query("unavoidable", "CMPS402.lecture", "L2")
    advice_case(advisor, catalogue, requests["single-course"], query, ALTERNATIVES, Verdict.NOT_UNAVOIDABLE)
    advice_case(advisor, catalogue, requests["forced"], query, FORCED, Verdict.UNAVOIDABLE)


def advice_outcomes(advisor, catalogue, requests):
    query = Query("unavoidable", "CMPS402.lecture", "L2")
    advice_case(advisor, catalogue, requests["blocked"], query, [], Verdict.BASE_INFEASIBLE)
    for limit_at in (1, 2):
        advice_case(advisor, catalogue, requests["forced"], query, FORCED, Verdict.INCONCLUSIVE, limit_at)


def advisor_restrictions(advisor, catalogue, requests):
    request = requests["single-course"]
    for query, expected in (
        (Query("take", "CMPS402.tutorial", "T4"), {"CMPS402.tutorial": {"T4"}}),
        (Query("avoid-day", day="Tue"), {"CMPS402.lecture": {"L1"}, "CMPS402.tutorial": {"T1", "T2", "T4"}}),
        (Query("unavoidable", "CMPS402.lecture", "L2"), {"CMPS402.lecture": {"L1"}}),
    ):
        allowed = advisor.make_restrictions(catalogue, request, query)
        require(isinstance(allowed, dict) and allowed.keys() <= set(request.components), "Use a dictionary of requested component IDs.")
        for component in request.components:
            all_ids = {section.identifier for section in catalogue.sections[component]}
            require(isinstance(allowed.get(component, all_ids), (set, frozenset))
                    and allowed.get(component, all_ids) == expected.get(component, all_ids),
                    f"Incorrect allowed section IDs for {component} in {query.kind}.")


def advisor_result_mapping(advisor, *_):
    witness = {"CMPS402.lecture": "L1"}
    require(advisor.base_failure(SolveResult(SolveStatus.SAT, {})) is None, "Even an empty SAT schedule permits the trial.")
    require(advisor.base_failure(SolveResult(SolveStatus.UNSAT)) == Advice(Verdict.BASE_INFEASIBLE),
            "An infeasible base stops before the what-if solve.")
    require(advisor.base_failure(SolveResult(SolveStatus.LIMIT)) == Advice(Verdict.INCONCLUSIVE), "A base limit is inconclusive.")
    for kind in ("take", "avoid-day", "unavoidable"):
        sat = Verdict.NOT_UNAVOIDABLE if kind == "unavoidable" else Verdict.POSSIBLE
        unsat = Verdict.UNAVOIDABLE if kind == "unavoidable" else Verdict.IMPOSSIBLE
        for trial, expected in (
            (SolveResult(SolveStatus.SAT, witness), Advice(sat, witness)),
            (SolveResult(SolveStatus.UNSAT), Advice(unsat)),
            (SolveResult(SolveStatus.LIMIT), Advice(Verdict.INCONCLUSIVE)),
        ):
            require(advisor.interpret_trial(kind, trial) == expected, f"Check the {kind} interpretation of {trial.status}.")


CHECKS = {
    "model-shape": ("model", "Fresh section-ID domains", model_shape),
    "model-links": ("model", "Linked and unlinked sections", model_links),
    "model-times": ("model", "Overlaps, identical slots and endpoints", model_times),
    "model-availability": ("model", "Blocked time and touching endpoints", model_availability),
    "unary": ("solver", "Unary filtering and empty domains", one_consistency),
    "mrv": ("solver", "MRV on current domains", mrv),
    "lcv": ("solver", "LCV, ties and non-mutation", lcv),
    "forward": ("solver", "Forward checking with multiple constraints", forward),
    "solver": ("solver", "Generic satisfiability and empty assignment", solver_general),
    "restoration": ("solver", "Backtrack and restore sibling domains", solver_restoration),
    "solver-integration": ("solver", "Helpers and unassigned-domain contract", solver_uses_helpers),
    "ac3-chain": ("solver", "AC-3: propagate through a chain", arc_propagation),
    "ac3-directions": ("solver", "AC-3: prune both directions", arc_directions),
    "ac3-wipeout": ("solver", "AC-3: detect empty domains", arc_wipeout),
    "ac3-local": ("solver", "AC-3: local consistency only", arc_local),
    "advisor-restrictions": ("advisor", "Build what-if allowed-ID sets", advisor_restrictions),
    "advisor-results": ("advisor", "Translate base and trial results", advisor_result_mapping),
    "take": ("advisor", "Can I take this section?", advice_take),
    "day": ("advisor", "Can I avoid this day?", advice_day),
    "unavoidable": ("advisor", "Is this section unavoidable?", advice_unavoidable),
    "outcomes": ("advisor", "Infeasible base and inconclusive runs", advice_outcomes),
}


def run_check(identifier, folder, catalogue, requests):
    module, title, check = CHECKS[identifier]
    check(load_part(folder, module), catalogue, requests)
    return {"status": "PASS"}
