"""Read immutable timetable records; this module does not formulate a CSP."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from types import MappingProxyType
from collections.abc import Mapping


@dataclass(frozen=True)
class Meeting:
    day: str
    start: int
    end: int


@dataclass(frozen=True)
class Section:
    identifier: str
    meeting: Meeting


@dataclass(frozen=True)
class Link:
    components: tuple[str, str]
    allowed: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class Catalogue:
    days: tuple[str, ...]
    sections: Mapping[str, tuple[Section, ...]]
    links: tuple[Link, ...]
    course_names: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class Request:
    components: tuple[str, ...]
    unavailable: tuple[Meeting, ...] = ()


@dataclass(frozen=True)
class Query:
    kind: str
    component: str | None = None
    section: str | None = None
    day: str | None = None


def minutes(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d|24:00", value, flags=re.ASCII):
        raise ValueError("Enter time as HH:MM, from 00:00 to 24:00.")
    hours, remainder = map(int, value.split(":"))
    return hours * 60 + remainder


def meeting(values, days):
    if not isinstance(values, (list, tuple)) or len(values) != 3 or values[0] not in days:
        raise ValueError("A meeting needs a declared day, start and end.")
    day, start_text, end_text = values
    start, end = minutes(start_text), minutes(end_text)
    if start >= end:
        raise ValueError("A meeting must finish after it starts.")
    return Meeting(day, start, end)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_catalogue(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
    days = tuple(payload["days"])
    if not days or not all(isinstance(day, str) and day for day in days) or len(set(days)) != len(days):
        raise ValueError("Catalogue days must be distinct nonempty labels.")
    sections = {}
    for component, choices in payload["components"].items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", component):
            raise ValueError(f"Expected COURSE.component, got {component}.")
        for identifier, slot in choices.items():
            if not identifier.strip() or not isinstance(slot, list) or len(slot) != 3 or not all(isinstance(part, str) for part in slot):
                raise ValueError(f"Section {component}/{identifier} needs exactly one [day, start, end] slot.")
        sections[component] = tuple(Section(identifier, meeting(slot, days)) for identifier, slot in choices.items())
    links, seen = [], set()
    for item in payload.get("links", []):
        endpoints = tuple(item["components"])
        if len(endpoints) != 2 or len(set(endpoints)) != 2 or any(endpoint not in sections for endpoint in endpoints):
            raise ValueError("A link must name two distinct catalogue components.")
        edge = frozenset(endpoints)
        if edge in seen:
            raise ValueError("Provide one allowed-pair list per linked component pair.")
        seen.add(edge)
        first, second = ({section.identifier for section in sections[endpoint]} for endpoint in endpoints)
        allowed = []
        for pair in item["allowed"]:
            if not isinstance(pair, list) or len(pair) != 2 or pair[0] not in first or pair[1] not in second:
                raise ValueError("A link must list section pairs in endpoint order.")
            allowed.append(tuple(pair))
        links.append(Link(endpoints, frozenset(allowed)))
    known = {component.partition(".")[0] for component in sections}
    names = payload.get("course_names", {})
    if not isinstance(names, dict) or not names.keys() <= known or not all(isinstance(name, str) and name.strip() for name in names.values()):
        raise ValueError("Course names must map known course codes to nonempty titles.")
    catalogue = Catalogue(days, MappingProxyType(sections), tuple(links), MappingProxyType(names))
    requests = {}
    for name, item in payload["requests"].items():
        courses = item["courses"]
        if not isinstance(courses, list) or not all(isinstance(course, str) for course in courses):
            raise ValueError("Each request needs a list of course IDs.")
        if len(set(courses)) != len(courses) or not set(courses) <= known:
            raise ValueError("A request must list distinct known courses.")
        components = tuple(component for component in sections if component.partition(".")[0] in courses)
        requests[name] = Request(components, tuple(meeting(value, days) for value in item.get("unavailable", [])))
    return catalogue, requests


def validate_query(catalogue, request, query):
    if query.kind == "schedule" and all(value is None for value in (query.component, query.section, query.day)):
        return
    if query.kind == "avoid-day" and query.day in catalogue.days and query.component is None and query.section is None:
        return
    if query.kind in {"take", "unavoidable"} and query.component in request.components and query.day is None:
        if any(section.identifier == query.section for section in catalogue.sections[query.component]):
            return
    raise ValueError("Invalid query. Choose a declared day or an existing section of a requested component.")
