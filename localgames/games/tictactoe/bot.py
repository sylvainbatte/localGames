from __future__ import annotations

import random
from functools import lru_cache
from typing import List, Optional, Tuple

from localgames.games.base import EASY, HARD, Bot, MEDIUM
from localgames.games.tictactoe.logic import WINNING_LINES

CENTER = 4
CORNERS = (0, 2, 6, 8)

# Per difficulty: chance to notice a winning cell, to notice a cell to block, and to play the
# perfect move instead of a random one once the tactics are out of the way.
WIN_CHANCE = {EASY: 0.35, MEDIUM: 0.9, HARD: 1.0}
BLOCK_CHANCE = {EASY: 0.3, MEDIUM: 0.75, HARD: 1.0}
BEST_CHANCE = {EASY: 0.0, MEDIUM: 0.0, HARD: 0.9}  # hard still slips once in a while


class TicTacToeBot(Bot):
    """Easy plays mostly at random, medium plays like a casual human, hard searches the whole game."""

    def __init__(
        self, my_index: int, difficulty: str = MEDIUM, rng: Optional[random.Random] = None
    ) -> None:
        super().__init__(my_index, difficulty)
        self._rng = rng or random.Random()

    def choose_move(self, state: dict) -> Optional[dict]:
        if state["over"] or state["turn"] != self.my_index:
            return None
        board = tuple(state["board"])
        free = [cell for cell, owner in enumerate(board) if owner is None]
        opponent = 1 - self.my_index
        for player, chance in ((self.my_index, WIN_CHANCE), (opponent, BLOCK_CHANCE)):
            cell = self._completing_cell(board, player)
            if cell is not None and self._rng.random() < chance[self.difficulty]:
                return {"cell": cell}
        if self._rng.random() < BEST_CHANCE[self.difficulty]:
            return {"cell": self._rng.choice(_best_cells(board, self.my_index))}
        if self.difficulty == EASY:
            return {"cell": self._rng.choice(free)}
        for preferred in ([CENTER], CORNERS, free):
            options = [cell for cell in preferred if cell in free]
            if options:
                return {"cell": self._rng.choice(options)}
        return None

    @staticmethod
    def _completing_cell(board: Tuple[Optional[int], ...], player: int) -> Optional[int]:
        for line in WINNING_LINES:
            owners = [board[cell] for cell in line]
            if owners.count(player) == 2 and owners.count(None) == 1:
                return line[owners.index(None)]
        return None


def _winner(board: Tuple[Optional[int], ...]) -> Optional[int]:
    for a, b, c in WINNING_LINES:
        if board[a] is not None and board[a] == board[b] == board[c]:
            return board[a]
    return None


@lru_cache(maxsize=None)
def _score(board: Tuple[Optional[int], ...], to_move: int, me: int) -> int:
    """Minimax value for `me`: +1 win, 0 draw, -1 loss, with perfect play from both sides."""
    winner = _winner(board)
    if winner is not None:
        return 1 if winner == me else -1
    free = [cell for cell, owner in enumerate(board) if owner is None]
    if not free:
        return 0
    scores = [
        _score(board[:cell] + (to_move,) + board[cell + 1:], 1 - to_move, me) for cell in free
    ]
    return max(scores) if to_move == me else min(scores)


def _best_cells(board: Tuple[Optional[int], ...], me: int) -> List[int]:
    free = [cell for cell, owner in enumerate(board) if owner is None]
    scored = {
        cell: _score(board[:cell] + (me,) + board[cell + 1:], 1 - me, me) for cell in free
    }
    best = max(scored.values())
    return [cell for cell, score in scored.items() if score == best]
