"""Package only submitted Python files, named using members' names and IDs."""

import ast
from pathlib import Path
import re
import zipfile


def read_identity(directory):
    path = Path(directory) / "student_info.py"
    values = {}
    for statement in ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path)).body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
            continue
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError("student_info.py must contain only a literal MEMBERS assignment.")
        name = statement.targets[0].id
        if name != "MEMBERS" or name in values:
            raise ValueError("Use one MEMBERS assignment containing member names and IDs only.")
        values[name] = ast.literal_eval(statement.value)
    return validate_identity(values.get("MEMBERS"))


def validate_identity(members):
    if not isinstance(members, list) or not 1 <= len(members) <= 2:
        raise ValueError("List one or two approved members in student_info.py.")
    cleaned = []
    for member in members:
        if not isinstance(member, dict) or not isinstance(member.get("name"), str) or not member["name"].strip():
            raise ValueError("Fill each member's full name in submission/student_info.py.")
        identifier = member.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", identifier):
            raise ValueError("Fill each student ID using letters, digits, underscores or hyphens.")
        cleaned.append({"name": member["name"].strip(), "id": identifier})
    if len({member["id"] for member in cleaned}) != len(cleaned):
        raise ValueError("Member IDs must be distinct.")
    return cleaned


def save_identity(directory, members):
    members = validate_identity(members)
    path = Path(directory) / "student_info.py"
    path.write_text('"""Student names and IDs."""\n\nMEMBERS = ' + repr(members) + "\n", encoding="utf-8")
    return members


def package_submission(directory, output_directory):
    directory = Path(directory).resolve()
    for name in ("model", "search", "heuristic", "student_info"):
        if not (directory / f"{name}.py").is_file():
            raise ValueError(f"Missing submission/{name}.py")
    members = read_identity(directory)
    parts = []
    for member in members:
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", member["name"])
        safe = "_".join(safe.split()).strip(" ._")[:60] or "Student"
        parts.append(safe + "_" + member["id"])
    filename = "__".join(parts) + ".zip"
    files = sorted(directory.rglob("*.py"))
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError("Python files must stay inside submission/; symlinks are not accepted.")
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / filename
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "submission/" + path.relative_to(directory).as_posix())
    return destination
