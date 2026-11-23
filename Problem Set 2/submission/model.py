"""Turn a timetable request into variables, domains and constraints."""

from scheduler.contracts import BinaryConstraint, Problem, UnaryConstraint

# scheduler/catalogue.py defines the parsed records:
# request.components is an ordered tuple, e.g. ("CMPS402.lecture", "CMPS402.tutorial").
# catalogue.sections[component] is a tuple of Section objects. Use section.identifier
# as the domain value; section.meeting gives day, start and end (integer minutes).
# request.unavailable is a tuple of Meeting records. catalogue.links is a tuple
# of Link records: .components orders the endpoints, .allowed holds section-ID pairs.
# scheduler/contracts.py stores callable predicates. The solver calls them later
# with section IDs, in endpoint order. Capture loop data with a factory or defaults.


def build_domains(catalogue, request):
    """Return a fresh dict[str, set[str]] containing every initial section ID."""
    raise NotImplementedError("Build one section-ID domain per requested component.")


def add_constraints(problem, catalogue, request):
    """Append constraint objects to problem.constraints; return None."""
    # Derive the rules from the timetable specification. Do not assign sections,
    # prune initial domains, or solve the problem here. Add private helpers if useful.
    raise NotImplementedError("Model the timetable rules in add_constraints.")


def build_problem(catalogue, request):
    """Build a fresh problem before each solve; leave this wiring in place."""
    problem = Problem(request.components, build_domains(catalogue, request), [])
    add_constraints(problem, catalogue, request)
    return problem
