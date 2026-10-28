from __future__ import annotations

from typing import List, Optional, Tuple

from localgames.games.base import Game, InvalidMove

BOARD_SIZE = 3
CELL_COUNT = BOARD_SIZE * BOARD_SIZE

WINNING_LINES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)


class TicTacToe(Game):
    """Board cells hold None (empty) or the index of the player who marked them."""

    def __init__(self) -> None:
        self._board: List[Optional[int]] = [None] * CELL_COUNT
        self._turn = 0
        self._winner: Optional[int] = None
        self._winning_line: Optional[Tuple[int, int, int]] = None

    def play(self, player_index: int, move: object) -> None:
        if self.is_over:
            raise InvalidMove("La partie est terminée.")
        if player_index != self._turn:
            raise InvalidMove("Ce n'est pas ton tour.")
        cell = self._parse_cell(move)
        if self._board[cell] is not None:
            raise InvalidMove("Cette case est déjà prise.")

        self._board[cell] = player_index
        self._winning_line = self._find_winning_line()
        if self._winning_line:
            self._winner = player_index
        self._turn = 1 - self._turn

    def state(self) -> dict:
        is_draw = self._winner is None and all(cell is not None for cell in self._board)
        return {
            "board": list(self._board),
            "turn": self._turn,
            "winner": self._winner,
            "line": list(self._winning_line) if self._winning_line else None,
            "draw": is_draw,
            "over": self._winner is not None or is_draw,
        }

    @staticmethod
    def _parse_cell(move: object) -> int:
        cell = move.get("cell") if isinstance(move, dict) else None
        if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell < CELL_COUNT:
            raise InvalidMove("Case invalide.")
        return cell

    def _find_winning_line(self) -> Optional[Tuple[int, int, int]]:
        for line in WINNING_LINES:
            first = self._board[line[0]]
            if first is not None and all(self._board[i] == first for i in line):
                return line
        return None
