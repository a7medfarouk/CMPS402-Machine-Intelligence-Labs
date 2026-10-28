"""Load only the submitted Python package, using the supplied staff runtime."""

from dataclasses import dataclass
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from types import ModuleType


@dataclass
class Bundle:
    Model: object
    solve: object
    heuristic: object


def load_bundle(directory):
    directory = Path(directory).resolve()
    name = "campus_submission_" + sha256(str(directory).encode()).hexdigest()[:12]
    package = ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package
    modules = {}
    for filename in ("model", "search", "heuristic"):
        path = directory / f"{filename}.py"
        specification = importlib.util.spec_from_file_location(f"{name}.{filename}", path)
        module = importlib.util.module_from_spec(specification)
        sys.modules[specification.name] = module
        specification.loader.exec_module(module)
        modules[filename] = module
    return Bundle(modules["model"].CampusProblem, modules["search"].solve, modules["heuristic"].heuristic)
