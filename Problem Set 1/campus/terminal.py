"""Rich presentation shared by the menu and human-readable commands."""

from contextlib import contextmanager
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from .feedback import LABELS


console = Console(highlight=False)
STYLES = {"ok": "green", "no_solution": "green", "local_only": "yellow", "not_implemented": "yellow", "wrong_answer": "red", "time_limit": "yellow", "resource_limit": "yellow", "runtime_error": "red"}


def verdict(status):
    return Text(LABELS.get(status, status), style=STYLES.get(status, "white"))


def display_path(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(Path(__file__).resolve().parents[1]))
    except ValueError:
        return str(path)


def show_table(headers, rows, title=None):
    result = Table(title=title, box=box.SIMPLE_HEAD, header_style="bold cyan", border_style="dim", padding=(0, 1), expand=True)
    for header in headers:
        result.add_column(header, overflow="fold")
    for row in rows:
        result.add_row(*(value if isinstance(value, Text) else Text(str(value)) for value in row))
    console.print(result)


def notice(message, title=None, style="cyan"):
    console.print(Panel(Text(str(message)), title=Text(title) if title else None, border_style=style, padding=(0, 1)))


def say(message="", style=None):
    console.print(Text(str(message), style=style))


def ask(message):
    return console.input(Text(message, style="bold cyan"))


def pause(message="Press Enter for the main menu."):
    ask(message)


@contextmanager
def progress(total, description, enabled=True):
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TaskProgressColumn(), TimeElapsedColumn(), console=console, transient=True, disable=not (enabled and console.is_terminal)) as display:
        task = display.add_task(description, total=total)

        def advance(label=""):
            display.update(task, advance=1, description=label or description)

        yield advance
