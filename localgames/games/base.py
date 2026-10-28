"""Contracts every game implements. Adding a game means implementing these."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional


class InvalidMove(Exception):
    """Raised by a game when a player's move is not allowed."""


class Game(ABC):
    """Server-side rules and state of one match. Knows nothing about networking."""

    @abstractmethod
    def play(self, player_index: int, move: object) -> None:
        """Applies a move or raises InvalidMove."""

    @abstractmethod
    def state(self) -> dict:
        """JSON-serializable snapshot sent to every player. Must contain an 'over' flag."""

    @property
    def is_over(self) -> bool:
        return bool(self.state()["over"])


class GameView(ABC):
    """Client-side rendering and input mapping for one player of a match."""

    controls: str = ""

    def __init__(self, my_index: int, player_names: List[str]) -> None:
        self.my_index = my_index
        self.player_names = player_names

    @abstractmethod
    def render(self, state: dict) -> List[str]:
        """Returns the lines to display for the given game state."""

    @abstractmethod
    def on_key(self, key: str, state: dict) -> Optional[dict]:
        """Maps a key press to a move to send to the server, or None."""


@dataclass(frozen=True)
class GameDefinition:
    """Everything the platform needs to list, host and display a game."""

    id: str
    name: str
    player_count: int
    create_game: Callable[[], Game]
    create_view: Callable[[int, List[str]], GameView]
