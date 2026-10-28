from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from localgames.games.base import Bot, Game, GameDefinition, InvalidMove
from localgames.protocol import ServerMessage, build_message

if TYPE_CHECKING:
    from localgames.server.lobby import Player


class Session:
    """A running match between the players who were matched for a game."""

    def __init__(
        self,
        definition: GameDefinition,
        players: List["Player"],
        bots: Optional[Dict[int, Bot]] = None,
    ) -> None:
        self.definition = definition
        self.players = players
        self._bots: Dict[int, Bot] = bots or {}
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
        self._run_bots()

    def play(self, player: "Player", move: object) -> None:
        """Applies the move, then tells everyone. Raises InvalidMove if rejected."""
        self._game.play(self.players.index(player), move)
        if not self.is_real_time:  # real-time games publish their state on every tick
            self._broadcast_state()
            self._run_bots()

    def tick(self) -> None:
        self._run_bots()
        self._game.tick()
        self._broadcast_state()

    def _run_bots(self) -> None:
        """Lets each computer player move, once per call, unless the match is over."""
        for index, bot in self._bots.items():
            if self.is_over:
                return
            move = bot.choose_move(self._game.state())
            if move is None:
                continue
            try:
                self._game.play(index, move)
            except InvalidMove:
                continue
            if not self.is_real_time:
                self._broadcast_state()

    def _broadcast_state(self) -> None:
        update = build_message(ServerMessage.GAME_UPDATE, state=self._game.state())
        for participant in self.players:
            participant.send(update)
