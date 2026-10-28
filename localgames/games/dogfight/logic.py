from __future__ import annotations

from typing import List, Optional

from localgames.games.base import Game, InvalidMove

WIDTH = 60
HEIGHT = 17
# Column of each plane's nose. Player 0 flies on the left facing right, player 1 on the right facing left.
PLANE_COLUMNS = (3, WIDTH - 4)
PLANE_HALF_HEIGHT = 1  # a plane covers 3 rows: its row and the one above and below
MIN_ROW = PLANE_HALF_HEIGHT
MAX_ROW = HEIGHT - 1 - PLANE_HALF_HEIGHT

MISSILE_SPEED = 1.2  # columns per tick
RELOAD_TICKS = 15
WIN_SCORE = 5
ROUND_DELAY_TICKS = 45


class Dogfight(Game):
    """Real-time duel: each pilot slides up and down and fires missiles straight ahead.

    A missile is a [column, row, owner] triple. It flies at constant speed along its row and
    scores for its owner when it crosses the enemy plane's column within the plane's rows. Two
    missiles flying toward each other on the same row destroy each other.
    """

    real_time = True

    def __init__(self) -> None:
        self._scores = [0, 0]
        self._winner: Optional[int] = None
        self._planes: List[int] = [HEIGHT // 2] * 2
        self._missiles: List[list] = []
        self._cooldowns = [0, 0]
        self._explosions: List[list] = []
        self._countdown = ROUND_DELAY_TICKS

    def play(self, player_index: int, move: object) -> None:
        if self._winner is not None:
            raise InvalidMove("La partie est terminée.")
        if not isinstance(move, dict):
            raise InvalidMove("Action invalide.")
        if move.get("fire") is True:
            self._fire(player_index)
            return
        direction = move.get("move")
        if isinstance(direction, bool) or direction not in (-1, 1):
            raise InvalidMove("Action invalide.")
        self._planes[player_index] = max(MIN_ROW, min(MAX_ROW, self._planes[player_index] + direction))

    def tick(self) -> None:
        if self._winner is not None:
            return
        if self._countdown > 0:
            self._countdown -= 1
            if self._countdown == 0:
                self._explosions = []
            return
        self._cooldowns = [max(0, c - 1) for c in self._cooldowns]
        self._move_missiles()

    def state(self) -> dict:
        return {
            "planes": list(self._planes),
            "missiles": [[round(m[0], 2), m[1], m[2]] for m in self._missiles],
            "cooldowns": list(self._cooldowns),
            "explosions": [list(e) for e in self._explosions],
            "scores": list(self._scores),
            "countdown": self._countdown,
            "winner": self._winner,
            "over": self._winner is not None,
        }

    def _fire(self, player_index: int) -> None:
        # Firing while reloading or between rounds is ignored: held keys would otherwise flood errors.
        if self._countdown > 0 or self._cooldowns[player_index] > 0:
            return
        column = PLANE_COLUMNS[0] + 1 if player_index == 0 else PLANE_COLUMNS[1] - 1
        self._missiles.append([float(column), self._planes[player_index], player_index])
        self._cooldowns[player_index] = RELOAD_TICKS

    def _move_missiles(self) -> None:
        hits: List[list] = []  # [shooter, column, row]
        flying: List[list] = []
        previous = {}
        for missile in self._missiles:
            before = missile[0]
            owner = missile[2]
            missile[0] += MISSILE_SPEED if owner == 0 else -MISSILE_SPEED
            target = 1 - owner
            plane_column = PLANE_COLUMNS[target]
            crossed = before < plane_column <= missile[0] if owner == 0 else before > plane_column >= missile[0]
            if crossed and abs(missile[1] - self._planes[target]) <= PLANE_HALF_HEIGHT:
                hits.append([owner, plane_column, self._planes[target]])
            elif 0 <= missile[0] <= WIDTH - 1:
                flying.append(missile)
                previous[id(missile)] = before
        if hits:
            self._end_round(hits)
            return
        self._missiles = self._without_collisions(flying, previous)

    @staticmethod
    def _without_collisions(missiles: List[list], previous: dict) -> List[list]:
        destroyed = set()
        for left in (m for m in missiles if m[2] == 0):
            for right in (m for m in missiles if m[2] == 1):
                if left[1] == right[1] and previous[id(left)] <= previous[id(right)] and left[0] >= right[0]:
                    destroyed.update((id(left), id(right)))
        return [m for m in missiles if id(m) not in destroyed]

    def _end_round(self, hits: List[list]) -> None:
        for shooter, _, _ in hits:
            self._scores[shooter] += 1
        self._explosions = [[column, row] for _, column, row in hits]
        self._missiles = []
        self._cooldowns = [0, 0]
        self._planes = [HEIGHT // 2] * 2
        self._countdown = ROUND_DELAY_TICKS
        best = max(self._scores)
        # Both planes hit on the same tick can tie at the target score: play on until one leads.
        if best >= WIN_SCORE and self._scores.count(best) == 1:
            self._winner = self._scores.index(best)
