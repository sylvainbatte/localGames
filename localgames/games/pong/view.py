from __future__ import annotations

import math
from typing import List, Optional

from localgames.ansi import BOLD, CYAN, DIM, GREEN, MAGENTA, RED, YELLOW, style
from localgames.config import TICK_INTERVAL_SECONDS
from localgames.games.base import GameView
from localgames.games.pong.logic import HEIGHT, PADDLE_COLUMNS, PADDLE_HEIGHT, WIDTH, WIN_SCORE

PLAYER_COLORS = (CYAN, MAGENTA)
SIDES = ("à gauche", "à droite")
UP_KEYS = ("UP", "w", "z")
DOWN_KEYS = ("DOWN", "s")


class PongView(GameView):
    controls = "↑/↓ (ou W/S) déplacer la raquette · Échap abandonner"

    def render(self, state: dict) -> List[str]:
        lines = [self._render_header(state)]
        lines.append("┌" + "─" * WIDTH + "┐")
        lines.extend("│" + row + "│" for row in self._render_field(state))
        lines.append("└" + "─" * WIDTH + "┘")
        lines.extend(["", self._render_status(state)])
        return lines

    def on_key(self, key: str, state: dict) -> Optional[dict]:
        if state["over"]:
            return None
        if key in UP_KEYS:
            return {"move": -1}
        if key in DOWN_KEYS:
            return {"move": 1}
        return None

    def _render_header(self, state: dict) -> str:
        left, right = (
            style(f"{name} {score}", BOLD, PLAYER_COLORS[index])
            for index, (name, score) in enumerate(zip(self.player_names, state["scores"]))
        )
        return f"{left}  —  {right}   " + style(f"(premier à {WIN_SCORE})", DIM)

    def _render_field(self, state: dict) -> List[str]:
        cells = [[" "] * WIDTH for _ in range(HEIGHT)]
        for row in range(0, HEIGHT, 2):
            cells[row][WIDTH // 2] = style("┆", DIM)
        for index, column in enumerate(PADDLE_COLUMNS):
            for row in range(state["paddles"][index], state["paddles"][index] + PADDLE_HEIGHT):
                cells[row][column] = style("█", BOLD, PLAYER_COLORS[index])
        ball_x, ball_y = state["ball"]
        cells[_clamp(round(ball_y), HEIGHT - 1)][_clamp(round(ball_x), WIDTH - 1)] = style("●", BOLD, YELLOW)
        return ["".join(row) for row in cells]

    def _render_status(self, state: dict) -> str:
        if state["winner"] == self.my_index:
            return style("Victoire !", BOLD, GREEN)
        if state["winner"] is not None:
            return style("Défaite…", BOLD, RED)
        side = f"Tu joues {SIDES[self.my_index]}"
        if state["serve_countdown"]:
            seconds = math.ceil(state["serve_countdown"] * TICK_INTERVAL_SECONDS)
            return style(f"{side} · service dans {seconds}…", BOLD)
        return style(side, DIM)


def _clamp(value: int, maximum: int) -> int:
    return max(0, min(maximum, value))
