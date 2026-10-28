"""Arrow-key selection with a plain-input fallback for restricted terminals."""

import os
import sys

from questionary import Choice, Style, select

from . import terminal


plain_menu = False
STYLE = Style([("question", "bold"), ("pointer", "fg:cyan bold"), ("highlighted", "fg:cyan bold"), ("answer", "fg:cyan"), ("instruction", "fg:gray")])


def configure(plain=False):
    global plain_menu
    plain_menu = plain


def arrow_supported():
    return not plain_menu and sys.stdin.isatty() and terminal.console.is_terminal and os.environ.get("TERM") != "dumb"


def arrow_choose(title, labels, zero_label="Back", **options):
    choices = [Choice(label, value=index) for index, label in enumerate(labels)] + [Choice(zero_label, value=-1)]
    answer = select(title, choices=choices, use_shortcuts=False, use_arrow_keys=True, instruction="Up/Down: move | Enter: select | Ctrl+C: cancel", style=STYLE, **options).unsafe_ask()
    return None if answer == -1 else answer


def numbered_choose(title, labels, zero_label="Back"):
    page, page_size = 0, 10
    while True:
        start = page * page_size
        visible = [(str(index + 1), labels[index]) for index in range(start, min(start + page_size, len(labels)))]
        terminal.show_table(["#", title], visible + [("0", zero_label)])
        if len(labels) > page_size:
            terminal.say(f"Page {page + 1}/{(len(labels) + page_size - 1) // page_size} | n: next | p: previous", "dim")
        value = terminal.ask("Choose a number: ").strip().lower()
        if value == "n" and (page + 1) * page_size < len(labels):
            page += 1
            continue
        if value == "p" and page:
            page -= 1
            continue
        if value == "0":
            return None
        if value.isdigit() and 1 <= int(value) <= len(labels):
            return int(value) - 1
        terminal.say("Please enter one of the listed numbers, or 0 to go back.", "yellow")


def choose(title, labels, zero_label="Back"):
    if arrow_supported():
        try:
            return arrow_choose(title, labels, zero_label)
        except (OSError, NotImplementedError):
            terminal.notice("Arrow-key input is unavailable in this console. Using plain input instead. You can also launch app.py --plain-menu.", "Terminal compatibility", "yellow")
    return numbered_choose(title, labels, zero_label)
