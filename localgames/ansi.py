"""Tiny ANSI styling helpers."""

import re

RESET = "\x1b[0m"

BOLD = "1"
DIM = "2"
REVERSE = "7"
RED = "31"
GREEN = "32"
YELLOW = "33"
MAGENTA = "35"
CYAN = "36"

_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def style(text: str, *codes: str) -> str:
    if not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}{RESET}"


def visible_length(text: str) -> int:
    return len(_ANSI_PATTERN.sub("", text))
