from __future__ import annotations

import threading
from typing import Dict, Iterable, List, Optional, Set

from localgames.config import MAX_NAME_LENGTH
from localgames.games.base import GameDefinition
from localgames.protocol import ServerMessage, build_message
from localgames.server.session import Session


class LobbyError(Exception):
    """A request the lobby refuses; its message is safe to show to the player."""


class Player:
    def __init__(self, name: str, channel) -> None:
        self.name = name
        self.session: Optional[Session] = None
        self._channel = channel

    def send(self, message: dict) -> None:
        try:
            self._channel.send(message)
        except OSError:
            pass  # the connection reader notices the disconnect and unregisters the player


class Lobby:
    """Tracks connected players, who waits for which game, and the running matches."""

    def __init__(self, definitions: Iterable[GameDefinition]) -> None:
        self._definitions: Dict[str, GameDefinition] = {d.id: d for d in definitions}
        self._waiting: Dict[str, List[Player]] = {game_id: [] for game_id in self._definitions}
        self._players: Dict[str, Player] = {}
        self._sessions: Set[Session] = set()
        self._lock = threading.RLock()

    @property
    def player_count(self) -> int:
        with self._lock:
            return len(self._players)

    def register(self, player: Player) -> None:
        with self._lock:
            if not 1 <= len(player.name) <= MAX_NAME_LENGTH:
                raise LobbyError(f"Le pseudo doit faire entre 1 et {MAX_NAME_LENGTH} caractères.")
            if player.name in self._players:
                raise LobbyError("Ce pseudo est déjà utilisé.")
            self._players[player.name] = player
            player.send(build_message(ServerMessage.WELCOME))
            self._broadcast_snapshot()

    def unregister(self, player: Player) -> None:
        with self._lock:
            self._withdraw(player)
            if self._players.get(player.name) is player:
                del self._players[player.name]
            self._broadcast_snapshot()

    def join(self, player: Player, game_id: object) -> None:
        with self._lock:
            definition = self._definitions.get(game_id)
            if definition is None:
                raise LobbyError("Jeu inconnu.")
            if player.session is not None:
                raise LobbyError("Tu es déjà en partie.")
            self._withdraw(player)
            queue = self._waiting[definition.id]
            queue.append(player)
            if len(queue) >= definition.player_count:
                matched = queue[:definition.player_count]
                del queue[:definition.player_count]
                self._start_session(definition, matched)
            self._broadcast_snapshot()

    def leave(self, player: Player) -> None:
        with self._lock:
            self._withdraw(player)
            self._broadcast_snapshot()

    def play(self, player: Player, move: object) -> None:
        with self._lock:
            session = player.session
            if session is None:
                raise LobbyError("Tu n'es pas en partie.")
            session.play(player, move)
            if session.is_over:
                self._close_session(session)
                self._broadcast_snapshot()

    def tick(self) -> None:
        """Advances every running real-time match by one step."""
        with self._lock:
            for session in [s for s in self._sessions if s.is_real_time]:
                session.tick()
                if session.is_over:
                    self._close_session(session)
                    self._broadcast_snapshot()

    def _start_session(self, definition: GameDefinition, players: List[Player]) -> None:
        session = Session(definition, players)
        self._sessions.add(session)
        for player in players:
            player.session = session
        session.start()

    def _close_session(self, session: Session) -> None:
        self._sessions.discard(session)
        for player in session.players:
            player.session = None

    def _withdraw(self, player: Player) -> None:
        """Removes the player from any waiting queue or running match."""
        session = player.session
        if session is not None:
            self._close_session(session)
            notice = build_message(ServerMessage.OPPONENT_LEFT, name=player.name)
            for other in session.players:
                if other is not player:
                    other.send(notice)
            return
        for queue in self._waiting.values():
            if player in queue:
                queue.remove(player)

    def _snapshot(self) -> dict:
        games = [
            {
                "id": definition.id,
                "name": definition.name,
                "player_count": definition.player_count,
                "waiting": [player.name for player in self._waiting[definition.id]],
                "playing": sum(
                    len(session.players)
                    for session in self._sessions
                    if session.definition.id == definition.id
                ),
            }
            for definition in self._definitions.values()
        ]
        return build_message(ServerMessage.LOBBY, online=list(self._players), games=games)

    def _broadcast_snapshot(self) -> None:
        snapshot = self._snapshot()
        for player in self._players.values():
            player.send(snapshot)
