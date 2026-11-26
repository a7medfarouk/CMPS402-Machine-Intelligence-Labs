"""Answer one what-if question using the supplied feasibility callback."""

from scheduler.contracts import Advice, SolveStatus, Verdict, SolveResult
from scheduler.catalogue import Catalogue, Request, Query

# scheduler/catalogue.py defines Query(kind, component, section, day).
# For "take" and "unavoidable", component and section are string IDs; day is None.
# For "avoid-day", day is a string; component and section are None.
# The app handles "schedule" itself; it is not passed here.
#
# solve_request({}) checks the base request. For example:
# solve_request({"CMPS402.tutorial": {"T4"}}) keeps only tutorial T4.
# Unmentioned domains are unchanged. A listed empty set removes every choice.
# Each call builds a fresh CSP and returns SolveResult(status, schedule):
# SAT = a witness dict (possibly {}), UNSAT = no schedule, LIMIT = inconclusive.
# Return Advice(Verdict.MEMBER, witness) or Advice(Verdict.MEMBER) without a witness.


def make_restrictions(catalogue: Catalogue, request: Request, query: Query):
    """Translate the question into allowed section IDs. Do not call the solver here."""
    # For an unavoidable question, test whether the named section can be avoided.
    if query.kind == "take":
        return {query.component: {query.section}}

    if query.kind == "unavoidable":
        return {
            query.component: {
                section.identifier
                for section in catalogue.sections[query.component]
                if section.identifier != query.section
            }
        }

    if query.kind == "avoid-day":
        restrictions = {}
        for component in request.components:
            restrictions[component] = {
                section.identifier
                for section in catalogue.sections[component]
                if section.meeting.day != query.day
            }
        return restrictions


def base_failure(base: SolveResult):
    """Return an Advice if the base prevents a trial, otherwise return None."""
    # Check base.status, not whether base.schedule is truthy: {} can be a valid
    #  witness.
    if base.status == SolveStatus.UNSAT:
        return Advice(Verdict.BASE_INFEASIBLE)
    if base.status == SolveStatus.LIMIT:
        return Advice(Verdict.INCONCLUSIVE)
    return None


def interpret_trial(kind: str, trial: SolveResult):
    """Turn the restricted solve into Advice; called only after a feasible base."""
    # For necessity, a successful trial is a counterexample, not proof of necessity.
    if trial.status == SolveStatus.LIMIT:
        return Advice(Verdict.INCONCLUSIVE)

    if kind == "unavoidable":
        if trial.status == SolveStatus.SAT:
            return Advice(Verdict.NOT_UNAVOIDABLE, trial.schedule)
        return Advice(Verdict.UNAVOIDABLE) 

    if trial.status == SolveStatus.SAT:
        return Advice(Verdict.POSSIBLE, trial.schedule)
    return Advice(Verdict.IMPOSSIBLE) 


def answer_query(catalogue, request, query, solve_request):
    """Run the base, stop if needed, then run and interpret one what-if solve."""
    base = solve_request({})
    stop = base_failure(base)
    if stop is not None:
        return stop
    restrictions = make_restrictions(catalogue, request, query)
    return interpret_trial(query.kind, solve_request(restrictions))
