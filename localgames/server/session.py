from __future__ import annotations

from typing import TYPE_CHECKING, List

from localgames.games.base import Game, GameDefinition
from localgames.protocol import ServerMessage, build_message

if TYPE_CHECKING:
    from localgames.server.lobby import Player


class Session:
    """A running match between the players who were matched for a game."""

    def __init__(self, definition: GameDefinition, players: List["Player"]) -> None:
        self.definition = definition
        self.players = players
        self._game: Game = definition.create_game()

    @property
    def is_over(self) -> bool:
        return self._game.is_over

    @property
    def is_real_time(self) -> bool:
        return self._game.real_time

    def start(self) -> None:
        names = [player.name for player in self.players]
        for index, player in enumerate(self.players):
            player.send(build_message(
                ServerMessage.GAME_START,
                game=self.definition.id,
                you=index,
                players=names,
                state=self._game.state(),
            ))

    def play(self, player: "Player", move: object) -> None:
        """Applies the move, then tells everyone. Raises InvalidMove if rejected."""
        self._game.play(self.players.index(player), move)
        if not self.is_real_time:  # real-time games publish their state on every tick
            self._broadcast_state()

    def tick(self) -> None:
        self._game.tick()
        self._broadcast_state()

    def _broadcast_state(self) -> None:
        update = build_message(ServerMessage.GAME_UPDATE, state=self._game.state())
        for participant in self.players:
            participant.send(update)
