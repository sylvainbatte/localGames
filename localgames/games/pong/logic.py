from __future__ import annotations

import random
from typing import List, Optional

from localgames.games.base import Game, InvalidMove

WIDTH = 50
HEIGHT = 15
PADDLE_HEIGHT = 4
PADDLE_STEP = 2
PADDLE_COLUMNS = (1, WIDTH - 2)
# The ball bounces when it reaches the column next to a paddle.
HIT_PLANES = (PADDLE_COLUMNS[0] + 1, PADDLE_COLUMNS[1] - 1)

WIN_SCORE = 7
SERVE_DELAY_TICKS = 60
START_SPEED = 0.7
MAX_SPEED = 1.5
SPEED_UP_PER_HIT = 1.06
MAX_VERTICAL_SPEED = 0.7
SERVE_VERTICAL_SPEED = 0.3


class Pong(Game):
    """Real-time match: one tick moves the ball, a move shifts the sender's paddle.

    Player 0 owns the left paddle and player 1 the right one. A paddle is described by the
    row of its top cell. The ball position is a float pair (column, row).
    """

    real_time = True

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._paddles: List[int] = [(HEIGHT - PADDLE_HEIGHT) // 2] * 2
        self._scores = [0, 0]
        self._winner: Optional[int] = None
        self._ball = [WIDTH / 2, HEIGHT / 2]
        self._velocity = [0.0, 0.0]
        self._serve_countdown = SERVE_DELAY_TICKS
        self._serve_toward = self._rng.randrange(2)
        self._prepare_serve(self._serve_toward)

    def play(self, player_index: int, move: object) -> None:
        if self._winner is not None:
            raise InvalidMove("La partie est terminée.")
        direction = move.get("move") if isinstance(move, dict) else None
        if isinstance(direction, bool) or direction not in (-1, 1):
            raise InvalidMove("Mouvement invalide.")
        top = self._paddles[player_index] + direction * PADDLE_STEP
        self._paddles[player_index] = max(0, min(HEIGHT - PADDLE_HEIGHT, top))

    def tick(self) -> None:
        if self._winner is not None:
            return
        if self._serve_countdown > 0:
            self._serve_countdown -= 1
            return
        self._move_ball()

    def state(self) -> dict:
        return {
            "paddles": list(self._paddles),
            "ball": [round(self._ball[0], 2), round(self._ball[1], 2)],
            "scores": list(self._scores),
            "serve_countdown": self._serve_countdown,
            "winner": self._winner,
            "over": self._winner is not None,
        }

    def _prepare_serve(self, toward: int) -> None:
        self._ball = [WIDTH / 2, HEIGHT / 2]
        horizontal = -START_SPEED if toward == 0 else START_SPEED
        self._velocity = [horizontal, self._rng.uniform(-SERVE_VERTICAL_SPEED, SERVE_VERTICAL_SPEED)]
        self._serve_countdown = SERVE_DELAY_TICKS

    def _move_ball(self) -> None:
        previous_x = self._ball[0]
        self._ball[0] += self._velocity[0]
        self._ball[1] += self._velocity[1]
        self._bounce_on_walls()
        self._bounce_on_paddles(previous_x)
        if self._ball[0] < 0:
            self._score(1)
        elif self._ball[0] > WIDTH - 1:
            self._score(0)

    def _bounce_on_walls(self) -> None:
        if self._ball[1] < 0:
            self._ball[1] = -self._ball[1]
            self._velocity[1] = -self._velocity[1]
        elif self._ball[1] > HEIGHT - 1:
            self._ball[1] = 2 * (HEIGHT - 1) - self._ball[1]
            self._velocity[1] = -self._velocity[1]

    def _bounce_on_paddles(self, previous_x: float) -> None:
        for index, plane in enumerate(HIT_PLANES):
            moving_toward = self._velocity[0] < 0 if index == 0 else self._velocity[0] > 0
            crossed = (previous_x - plane) * (self._ball[0] - plane) <= 0 and previous_x != plane
            if not (moving_toward and crossed):
                continue
            top = self._paddles[index]
            if not top - 0.5 <= self._ball[1] <= top + PADDLE_HEIGHT - 0.5:
                continue
            offset = (self._ball[1] - (top + (PADDLE_HEIGHT - 1) / 2)) / (PADDLE_HEIGHT / 2)
            speed = min(MAX_SPEED, abs(self._velocity[0]) * SPEED_UP_PER_HIT)
            self._velocity[0] = speed if index == 0 else -speed
            self._velocity[1] = max(-1.0, min(1.0, offset)) * MAX_VERTICAL_SPEED
            self._ball[0] = plane
            return

    def _score(self, scorer: int) -> None:
        self._scores[scorer] += 1
        if self._scores[scorer] >= WIN_SCORE:
            self._winner = scorer
            return
        self._prepare_serve(toward=1 - scorer)
