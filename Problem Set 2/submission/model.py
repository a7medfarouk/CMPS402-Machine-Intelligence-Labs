"""Turn a timetable request into variables, domains and constraints."""
from typing import Tuple

from scheduler.catalogue import Catalogue, Meeting, Request
from scheduler.contracts import BinaryConstraint, Problem, UnaryConstraint

# scheduler/catalogue.py defines the parsed records:
# request.components is an ordered tuple, e.g. ("CMPS402.lecture", "CMPS402.tutorial").
# catalogue.sections[component] is a tuple of Section objects. Use section.identifier
# as the domain value; section.meeting gives day, start and end (integer minutes).
# request.unavailable is a tuple of Meeting records. catalogue.links is a tuple
# of Link records: .components orders the endpoints, .allowed holds section-ID pairs.
# scheduler/contracts.py stores callable predicates. The solver calls them later
# with section IDs, in endpoint order. Capture loop data with a factory or defaults.


def build_domains(catalogue : Catalogue, request: Request):
    """Return a fresh dict[str, set[str]] containing every initial section ID."""
    domains: dict[str, set[str]] = {}
    for component in request.components:
        domains.setdefault(component, set())
        for section in catalogue.sections[component]:
            domains[component].add(section.identifier)
    return domains


def add_constraints(problem: Problem, catalogue: Catalogue, request: Request):
    """Append constraint objects to problem.constraints; return None."""
    # Derive the rules from the timetable specification. Do not assign sections,
    # prune initial domains, or solve the problem here. Add private helpers if useful.
    def unary_unavailable_constraint(section_id: str, component: str) -> bool: 
        """Checks the time of the section against the student's unavailable time."""
        available: bool = True
        for section in catalogue.sections[component]:
            if section.identifier == section_id:
                section_meeting: Meeting = section.meeting
                break
        for meeting in request.unavailable:
            if meeting.day == section_meeting.day and meeting.end > section_meeting.start and section_meeting.end > meeting.start:
                available = False
        return available
    def binary_overlap_constraint(component1: str, component2: str, section_id1: str, section_id2: str) -> bool:
        """Checks binary overlapping constraint between 2 sections"""
        for section in catalogue.sections[component1]:
            if section.identifier == section_id1:
                section_meeting1 = section.meeting
                break
        for section in catalogue.sections[component2]:
            if section.identifier == section_id2:
                section_meeting2 = section.meeting
                break 
        if section_meeting1.day == section_meeting2.day and section_meeting1.start < section_meeting2.end and section_meeting2.start < section_meeting1.end:
            return False
        else: 
            return True
    def binary_linked_constraint(component1: str, component2: str, section_id1: str, section_id2: str) -> bool:
        """Checks binary linked constraints between 2 sections"""
        section_pair: Tuple[str, str] = (component1, component2)
        id_pair: Tuple[str, str] = (section_id1, section_id2)
        for link in catalogue.links:
            if section_pair == link.components:
                if id_pair in link.allowed:
                    return True
                else: 
                    return False
    for component in request.components:
        condition = lambda section_id, component = component: (
            unary_unavailable_constraint(section_id, component)
        )
        problem.constraints.append(
            UnaryConstraint(
                variable=component,
                condition=condition
            )
        )
    for i, component1 in enumerate(request.components):
        for component2 in request.components[i + 1:]:
            condition = lambda section_id1, section_id2, component1=component1, component2=component2: (
                binary_overlap_constraint(
                    component1, component2, section_id1, section_id2
                )
            )

            problem.constraints.append(
                BinaryConstraint(
                    variables=(component1, component2),
                    condition=condition
                )
            )
    for link in catalogue.links:
        component1, component2 = link.components

        if component1 in request.components and component2 in request.components:
            condition = lambda section_id1, section_id2, component1=component1, component2=component2: (
                binary_linked_constraint(
                    component1, component2, section_id1, section_id2
                )
            )

            problem.constraints.append(
                BinaryConstraint(
                    variables=(component1, component2),
                    condition=condition
                )
            )
    return None


def build_problem(catalogue: Catalogue, request: Request):
    """Build a fresh problem before each solve; leave this wiring in place."""
    problem = Problem(request.components, build_domains(catalogue, request), [])
    add_constraints(problem, catalogue, request)
    return problem
