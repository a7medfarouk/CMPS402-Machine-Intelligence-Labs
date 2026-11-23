"""Readable output without treating student data as Rich markup."""

import os
import sys

from questionary import Choice, Style, select
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


console = Console(highlight=False)
STYLE = Style([("pointer", "fg:cyan bold"), ("highlighted", "fg:cyan bold"), ("answer", "fg:cyan")])
STYLES = {"PASS": "green", "TIME LIMIT": "yellow", "NOT IMPLEMENTED": "yellow",
          "NOT ATTEMPTED": "dim", "INVALID REQUEST": "yellow", "WRONG ANSWER": "red", "RUNTIME ERROR": "red"}


def verdict(status):
    return Text(status, style=STYLES.get(status, "white"))


def notice(message, title="Adversarial Search", style="cyan"):
    console.print(Panel(Text(str(message)), title=Text(title), border_style=style))


def show_table(headers, rows, title=None):
    table = Table(title=Text(title) if title else None, header_style="bold cyan", border_style="dim")
    for header in headers:
        table.add_column(header, overflow="fold")
    for row in rows:
        table.add_row(*(value if isinstance(value, Text) else Text(str(value)) for value in row))
    console.print(table)


def choose(title, labels, plain=False, back="Back"):
    if not plain and sys.stdin.isatty() and console.is_terminal and os.environ.get("TERM") != "dumb":
        try:
            items = [Choice(label, value=index) for index, label in enumerate(labels)] + [Choice(back, value=-1)]
            answer = select(title, choices=items, use_shortcuts=False, style=STYLE,
                            instruction="Up/Down: move | Enter: select | Ctrl+C: cancel").unsafe_ask()
            return None if answer == -1 else answer
        except (OSError, NotImplementedError):
            notice("Arrow-key input is unavailable here. Switching to numbered input.", style="yellow")
    while True:
        rows = [(index + 1, label) for index, label in enumerate(labels)]
        show_table(("#", title), [*rows, (0, back)])
        value = input("Choose a number: ").strip()
        if value == "0":
            return None
        if value.isdecimal() and len(value) < 8 and 1 <= int(value) <= len(labels):
            return int(value) - 1
        console.print("Enter a listed number.", style="yellow")
