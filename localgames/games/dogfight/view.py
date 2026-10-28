from __future__ import annotations

import math
from typing import List, Optional

from localgames.ansi import BOLD, CYAN, DIM, GREEN, MAGENTA, RED, YELLOW, style
from localgames.config import TICK_INTERVAL_SECONDS
from localgames.games.base import GameView
from localgames.games.dogfight.logic import (
    HEIGHT, PLANE_COLUMNS, PLANE_HALF_HEIGHT, RELOAD_TICKS, WIDTH, WIN_SCORE,
)

PLAYER_COLORS = (CYAN, MAGENTA)
SIDES = ("à gauche", "à droite")
UP_KEYS = ("UP", "w", "z")
DOWN_KEYS = ("DOWN", "s")
FIRE_KEYS = (" ", "ENTER")


class DogfightView(GameView):
    controls = "↑/↓ (ou W/S) monter/descendre · Espace tirer un missile · Échap abandonner"

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
        if key in FIRE_KEYS:
            return {"fire": True}
        return None

    def _render_header(self, state: dict) -> str:
        left, right = (
            style(f"{name} {score}", BOLD, PLAYER_COLORS[index])
            for index, (name, score) in enumerate(zip(self.player_names, state["scores"]))
        )
        return f"{left}  —  {right}   " + style(f"(premier à {WIN_SCORE})", DIM)

    def _render_field(self, state: dict) -> List[str]:
        cells = [[" "] * WIDTH for _ in range(HEIGHT)]
        for index, row in enumerate(state["planes"]):
            self._draw_plane(cells, index, row)
        for x, row, owner in state["missiles"]:
            cells[row][_clamp(round(x), WIDTH - 1)] = style("━", BOLD, YELLOW)
        for column, row in state["explosions"]:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if 0 <= row + dy < HEIGHT and 0 <= column + dx < WIDTH:
                        cells[row + dy][column + dx] = style("✸" if dx == dy == 0 else "*", BOLD, RED)
        return ["".join(row) for row in cells]

    @staticmethod
    def _draw_plane(cells: List[List[str]], index: int, row: int) -> None:
        color = PLAYER_COLORS[index]
        nose = PLANE_COLUMNS[index]
        if index == 0:
            body, wing_column, wing_top, wing_bottom = ["═", "═", ">"], nose - 1, "╲", "╱"
            first_column = nose - 2
        else:
            body, wing_column, wing_top, wing_bottom = ["<", "═", "═"], nose + 1, "╱", "╲"
            first_column = nose
        for offset, char in enumerate(body):
            cells[row][first_column + offset] = style(char, BOLD, color)
        cells[row - PLANE_HALF_HEIGHT][wing_column] = style(wing_top, BOLD, color)
        cells[row + PLANE_HALF_HEIGHT][wing_column] = style(wing_bottom, BOLD, color)

    def _render_status(self, state: dict) -> str:
        if state["winner"] == self.my_index:
            return style("Victoire !", BOLD, GREEN)
        if state["winner"] is not None:
            return style("Défaite…", BOLD, RED)
        side = f"Tu pilotes l'avion {SIDES[self.my_index]}"
        if state["countdown"]:
            seconds = math.ceil(state["countdown"] * TICK_INTERVAL_SECONDS)
            return style(f"{side} · reprise dans {seconds}…", BOLD)
        cooldown = state["cooldowns"][self.my_index]
        if cooldown:
            filled = RELOAD_TICKS - cooldown
            return style(f"{side} · rechargement ", DIM) + style("█" * filled + "░" * cooldown, YELLOW)
        return style(f"{side} · ", DIM) + style("missile prêt", BOLD, GREEN)


def _clamp(value: int, maximum: int) -> int:
    return max(0, min(maximum, value))
