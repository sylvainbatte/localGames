from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from localgames.games.base import EASY, HARD, Bot, MEDIUM
from localgames.games.dogfight.logic import MAX_ROW, MIN_ROW, PLANE_COLUMNS, PLANE_HALF_HEIGHT


@dataclass(frozen=True)
class _Skill:
    reaction_ticks: int  # the bot acts once every this many ticks
    aim_error: int  # rows of tolerated misalignment before firing, also the random error on its aim
    dodge_chance: float  # probability, at each action, of sidestepping a missile that would hit it
    fire_chance: float  # probability of firing when aligned and reloaded


SKILLS = {
    EASY: _Skill(reaction_ticks=6, aim_error=1, dodge_chance=0.0, fire_chance=0.3),
    MEDIUM: _Skill(reaction_ticks=4, aim_error=1, dodge_chance=0.4, fire_chance=0.6),
    HARD: _Skill(reaction_ticks=2, aim_error=0, dodge_chance=0.8, fire_chance=1.0),
}


class DogfightBot(Bot):
    """Easy chases the enemy and fires clumsily, medium sometimes dodges, hard usually dodges and aims precisely."""

    def __init__(
        self, my_index: int, difficulty: str = MEDIUM, rng: Optional[random.Random] = None
    ) -> None:
        super().__init__(my_index, difficulty)
        self._skill = SKILLS[difficulty]
        self._rng = rng or random.Random()
        self._ticks = 0

    def choose_move(self, state: dict) -> Optional[dict]:
        self._ticks += 1
        if state["over"] or state["countdown"] or self._ticks % self._skill.reaction_ticks:
            return None
        mine = state["planes"][self.my_index]
        if self._rng.random() < self._skill.dodge_chance:
            threat = self._threat_row(state, mine)
            if threat is not None:
                return {"move": self._escape_direction(mine, threat)}
        enemy = state["planes"][1 - self.my_index]
        gap = enemy - mine
        if abs(gap) <= self._skill.aim_error:
            if state["cooldowns"][self.my_index] == 0 and self._rng.random() < self._skill.fire_chance:
                return {"fire": True}
            return None
        return {"move": 1 if gap > 0 else -1}

    def _threat_row(self, state: dict, mine: int) -> Optional[int]:
        """Row of the nearest enemy missile that would hit the plane if it stayed put."""
        column = PLANE_COLUMNS[self.my_index]
        nearest = None
        for x, row, owner in state["missiles"]:
            incoming = owner != self.my_index and (x > column if self.my_index == 0 else x < column)
            if incoming and abs(row - mine) <= PLANE_HALF_HEIGHT + 1:
                if nearest is None or abs(x - column) < abs(nearest[0] - column):
                    nearest = (x, row)
        return None if nearest is None else nearest[1]

    @staticmethod
    def _escape_direction(mine: int, threat_row: int) -> int:
        if mine == threat_row:
            return 1 if mine - MIN_ROW < MAX_ROW - mine else -1
        direction = 1 if mine > threat_row else -1
        if not MIN_ROW <= mine + direction <= MAX_ROW:
            return -direction
        return direction
