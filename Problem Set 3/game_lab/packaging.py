"""Validate literal member details and package only submission Python files."""

import ast
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile


REQUIRED = {"search.py", "evaluation.py", "student_info.py"}


def validate_members(members):
    if not isinstance(members, list) or len(members) not in (1, 2):
        raise ValueError("Enter one or two members in Submit > Enter member details, or set MEMBERS in student_info.py.")
    cleaned = []
    for member in members:
        if not isinstance(member, dict) or set(member) != {"name", "id"}:
            raise ValueError("Each member must have name and id fields.")
        name, identifier = member["name"], member["id"]
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            raise ValueError("Enter each member's full name, up to 100 characters.")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", identifier):
            raise ValueError("Use an ID containing letters, digits, hyphens or underscores.")
        cleaned.append({"name": name.strip(), "id": identifier})
    if len({member["id"].casefold() for member in cleaned}) != len(cleaned):
        raise ValueError("Member IDs must be distinct.")
    return cleaned


def read_members(directory):
    source = (directory / "student_info.py").read_text(encoding="utf-8-sig")
    statements = [statement for statement in ast.parse(source).body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str)
    )]
    if len(statements) != 1:
        raise ValueError("Use a single literal MEMBERS assignment in student_info.py.")
    statement = statements[0]
    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name) or statement.targets[0].id != "MEMBERS":
        raise ValueError("Use a single literal MEMBERS assignment in student_info.py.")
    return validate_members(ast.literal_eval(statement.value))


def save_members(directory, members):
    members = validate_members(members)
    (directory / "student_info.py").write_text("MEMBERS = " + repr(members) + "\n", encoding="utf-8")


def python_files(directory):
    directory = directory.resolve()
    paths = sorted(directory.rglob("*.py"))
    if not REQUIRED <= {path.name for path in paths if path.parent == directory}:
        raise ValueError("submission/ must contain search.py, evaluation.py and student_info.py.")
    if any(not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(directory) for path in paths):
        raise ValueError("Submission must contain ordinary Python files within submission/.")
    if len(paths) > 200 or sum(path.stat().st_size for path in paths) > 5 * 1024 * 1024:
        raise ValueError("Submission exceeds 200 files or 5 MiB.")
    return paths


def package(directory, output):
    directory = directory.resolve()
    members = read_members(directory)
    parts = []
    for member in members:
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", member["name"])
        parts.append(("_".join(safe.split()).strip(" ._")[:60] or "Student") + "_" + member["id"])
    paths = python_files(directory)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / ("__".join(parts) + ".zip")
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, "submission/" + path.relative_to(directory).as_posix())
    return destination
