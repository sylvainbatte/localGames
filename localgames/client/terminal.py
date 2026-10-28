"""Raw terminal access: full-screen drawing and key reading, on POSIX and Windows."""

from __future__ import annotations

import os
import shutil
import sys
import time
from typing import List, Optional

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import msvcrt
else:
    import select
    import termios
    import tty

_ENTER_SCREEN = "\x1b[?1049h\x1b[?25l"
_LEAVE_SCREEN = "\x1b[?25h\x1b[?1049l"
_HOME_AND_CLEAR = "\x1b[H\x1b[J"

_ARROWS = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}
_WINDOWS_ARROWS = {"H": "UP", "P": "DOWN", "M": "RIGHT", "K": "LEFT"}
_ESCAPE_FOLLOW_UP_SECONDS = 0.05


class Terminal:
    """Context manager owning the screen. read_key returns names like UP, ENTER, ESC or a character."""

    def __enter__(self) -> "Terminal":
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise SystemExit("LocalGames doit être lancé dans un terminal interactif.")
        if IS_WINDOWS:
            os.system("")  # enables ANSI escape sequence processing on Windows 10+
        else:
            self._fd = sys.stdin.fileno()
            self._saved_attributes = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
        self._write(_ENTER_SCREEN)
        return self

    def __exit__(self, *exc_info) -> None:
        self._write(_LEAVE_SCREEN)
        if not IS_WINDOWS:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved_attributes)

    def draw(self, lines: List[str]) -> None:
        """Replaces the whole screen with the given lines."""
        self._write(_HOME_AND_CLEAR + "\r\n".join(lines))

    @staticmethod
    def width() -> int:
        return shutil.get_terminal_size((80, 24)).columns

    def read_key(self, timeout: float) -> Optional[str]:
        """Waits up to timeout seconds for a key; returns None if none was pressed."""
        return self._read_key_windows(timeout) if IS_WINDOWS else self._read_key_posix(timeout)

    @staticmethod
    def _write(text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    def _read_key_posix(self, timeout: float) -> Optional[str]:
        first = self._read_char(timeout)
        if first is None:
            return None
        if first == "\x1b":
            return self._read_escape_sequence()
        return _name_for_character(first)

    def _read_escape_sequence(self) -> str:
        if self._read_char(_ESCAPE_FOLLOW_UP_SECONDS) not in ("[", "O"):
            return "ESC"
        final = self._read_char(_ESCAPE_FOLLOW_UP_SECONDS)
        while final is not None and final in "0123456789;":
            final = self._read_char(_ESCAPE_FOLLOW_UP_SECONDS)
        return _ARROWS.get(final or "", "")

    def _read_char(self, timeout: float) -> Optional[str]:
        if not select.select([self._fd], [], [], timeout)[0]:
            return None
        data = os.read(self._fd, 1)
        if not data:
            raise EOFError("Entrée standard fermée")
        while True:  # complete a multi-byte UTF-8 character
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                if len(data) >= 4:
                    return ""
                data += os.read(self._fd, 1)

    @staticmethod
    def _read_key_windows(timeout: float) -> Optional[str]:
        deadline = time.monotonic() + timeout
        while not msvcrt.kbhit():
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)
        char = msvcrt.getwch()
        if char in ("\x00", "\xe0"):
            return _WINDOWS_ARROWS.get(msvcrt.getwch(), "")
        return _name_for_character(char)


def _name_for_character(char: str) -> str:
    if char == "\x03":
        raise KeyboardInterrupt
    if char in ("\r", "\n"):
        return "ENTER"
    if char in ("\x7f", "\x08"):
        return "BACKSPACE"
    return char
