"""Answer one what-if question using the supplied feasibility callback."""

from scheduler.contracts import Advice, SolveStatus, Verdict

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


def make_restrictions(catalogue, request, query):
    """Translate the question into allowed section IDs. Do not call the solver here."""
    # For an unavoidable question, test whether the named section can be avoided.
    raise NotImplementedError("Build the allowed-ID sets for each question.")


def base_failure(base):
    """Return an Advice if the base prevents a trial, otherwise return None."""
    # Check base.status, not whether base.schedule is truthy: {} can be a valid witness.
    raise NotImplementedError("Decide whether the unchanged request permits a trial.")


def interpret_trial(kind, trial):
    """Turn the restricted solve into Advice; called only after a feasible base."""
    # For necessity, a successful trial is a counterexample, not proof of necessity.
    raise NotImplementedError("Translate the trial status into the appropriate verdict.")


def answer_query(catalogue, request, query, solve_request):
    """Run the base, stop if needed, then run and interpret one what-if solve."""
    base = solve_request({})
    stop = base_failure(base)
    if stop is not None:
        return stop
    restrictions = make_restrictions(catalogue, request, query)
    return interpret_trial(query.kind, solve_request(restrictions))
