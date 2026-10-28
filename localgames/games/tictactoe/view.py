from __future__ import annotations

from typing import List, Optional

from localgames.ansi import BOLD, CYAN, DIM, GREEN, MAGENTA, RED, REVERSE, YELLOW, style
from localgames.games.base import GameView
from localgames.games.tictactoe.logic import BOARD_SIZE, CELL_COUNT

MARKS = ("X", "O")
MARK_COLORS = (CYAN, MAGENTA)
CELL_WIDTH = 5
HORIZONTAL_RULE = "─" * CELL_WIDTH
CURSOR_MOVES = {"UP": -BOARD_SIZE, "DOWN": BOARD_SIZE, "LEFT": -1, "RIGHT": 1}


class TicTacToeView(GameView):
    controls = "←↑↓→ déplacer · Entrée jouer · 1-9 case directe · Échap abandonner"

    def __init__(self, my_index: int, player_names: List[str]) -> None:
        super().__init__(my_index, player_names)
        self._cursor = CELL_COUNT // 2

    def render(self, state: dict) -> List[str]:
        lines = [self._render_header(), ""]
        lines.extend(self._render_board(state))
        lines.extend(["", self._render_status(state)])
        return lines

    def on_key(self, key: str, state: dict) -> Optional[dict]:
        if key in CURSOR_MOVES:
            self._move_cursor(key)
            return None
        if state["over"] or state["turn"] != self.my_index:
            return None
        if key in ("ENTER", " "):
            return {"cell": self._cursor}
        if key.isdigit() and key != "0":
            self._cursor = int(key) - 1
            return {"cell": self._cursor}
        return None

    def _move_cursor(self, key: str) -> None:
        row, column = divmod(self._cursor, BOARD_SIZE)
        if key in ("UP", "DOWN"):
            row = (row + CURSOR_MOVES[key] // BOARD_SIZE) % BOARD_SIZE
        else:
            column = (column + CURSOR_MOVES[key]) % BOARD_SIZE
        self._cursor = row * BOARD_SIZE + column

    def _render_header(self) -> str:
        players = [
            style(f"{name} ({MARKS[index]})", BOLD, MARK_COLORS[index])
            for index, name in enumerate(self.player_names)
        ]
        return "  vs  ".join(players)

    def _render_board(self, state: dict) -> List[str]:
        lines: List[str] = []
        for row in range(BOARD_SIZE):
            cells = [self._render_cell(row * BOARD_SIZE + column, state) for column in range(BOARD_SIZE)]
            for line_index in range(3):
                lines.append("│".join(cell[line_index] for cell in cells))
            if row < BOARD_SIZE - 1:
                lines.append("┼".join([HORIZONTAL_RULE] * BOARD_SIZE))
        return lines

    def _render_cell(self, cell: int, state: dict) -> List[str]:
        owner = state["board"][cell]
        winning = cell in (state["line"] or ())
        codes: List[str] = []
        if owner is None:
            middle = f"  {cell + 1}  "
            codes.append(DIM)
        else:
            middle = f"  {MARKS[owner]}  "
            codes.extend([BOLD, GREEN if winning else MARK_COLORS[owner]])
        if cell == self._cursor and not state["over"]:
            codes.append(REVERSE)
        blank = " " * CELL_WIDTH
        return [style(text, *codes) for text in (blank, middle, blank)]

    def _render_status(self, state: dict) -> str:
        if state["winner"] == self.my_index:
            return style("Victoire !", BOLD, GREEN)
        if state["winner"] is not None:
            return style("Défaite…", BOLD, RED)
        if state["draw"]:
            return style("Égalité.", BOLD, YELLOW)
        if state["turn"] == self.my_index:
            return style(f"À toi de jouer ({MARKS[self.my_index]})", BOLD)
        return style(f"Au tour de {self.player_names[state['turn']]}…", DIM)
