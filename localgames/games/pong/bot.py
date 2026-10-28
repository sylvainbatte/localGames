from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from localgames.games.base import EASY, HARD, Bot, MEDIUM
from localgames.games.pong.logic import HEIGHT, HIT_PLANES, PADDLE_HEIGHT


@dataclass(frozen=True)
class _Skill:
    reaction_ticks: int  # the bot acts once every this many ticks
    dead_zone: float  # rows between paddle center and target tolerated before moving
    aim_error: float  # half-width of the random error on the target row, redrawn per rally shot
    predicts: bool  # aims where the ball will land instead of following its current row


SKILLS = {
    EASY: _Skill(reaction_ticks=5, dead_zone=2.0, aim_error=2.5, predicts=False),
    MEDIUM: _Skill(reaction_ticks=3, dead_zone=1.0, aim_error=1.5, predicts=False),
    HARD: _Skill(reaction_ticks=2, dead_zone=0.5, aim_error=1.4, predicts=True),
}


class PongBot(Bot):
    """Easy lags and follows loosely, medium follows the ball, hard predicts bounces but is imprecise."""

    def __init__(
        self, my_index: int, difficulty: str = MEDIUM, rng: Optional[random.Random] = None
    ) -> None:
        super().__init__(my_index, difficulty)
        self._skill = SKILLS[difficulty]
        self._rng = rng or random.Random()
        self._ticks = 0
        self._previous_ball: Optional[list] = None
        self._aim_offset = 0.0
        self._was_incoming = False

    def choose_move(self, state: dict) -> Optional[dict]:
        self._ticks += 1
        ball = state["ball"]
        velocity_x = 0.0 if self._previous_ball is None else ball[0] - self._previous_ball[0]
        velocity_y = 0.0 if self._previous_ball is None else ball[1] - self._previous_ball[1]
        self._previous_ball = list(ball)
        incoming = velocity_x < 0 if self.my_index == 0 else velocity_x > 0
        if incoming and not self._was_incoming:
            self._aim_offset = self._rng.uniform(-self._skill.aim_error, self._skill.aim_error)
        self._was_incoming = incoming
        if state["over"] or self._ticks % self._skill.reaction_ticks:
            return None
        target = self._target_row(ball, velocity_x, velocity_y, incoming)
        center = state["paddles"][self.my_index] + (PADDLE_HEIGHT - 1) / 2
        gap = target - center
        if abs(gap) <= self._skill.dead_zone:
            return None
        return {"move": 1 if gap > 0 else -1}

    def _target_row(self, ball: list, velocity_x: float, velocity_y: float, incoming: bool) -> float:
        if not self._skill.predicts:
            return ball[1] + self._aim_offset
        if not incoming:
            return (HEIGHT - 1) / 2  # drift back to the middle while the ball goes away
        plane = HIT_PLANES[self.my_index]
        travel = (plane - ball[0]) / velocity_x
        return _fold(ball[1] + velocity_y * travel) + self._aim_offset


def _fold(row: float) -> float:
    """Reflects a row on the top and bottom walls, like the ball does."""
    span = HEIGHT - 1
    row %= 2 * span
    return row if row <= span else 2 * span - row
