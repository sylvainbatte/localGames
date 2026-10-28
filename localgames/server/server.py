from __future__ import annotations

import os
import socket
import threading
from typing import Callable, Dict, Optional

from localgames.config import DISCOVERY_PORT, SERVER_PORT, TICK_INTERVAL_SECONDS
from localgames.discovery import DiscoveryResponder
from localgames.games.base import InvalidMove
from localgames.games.registry import GAME_DEFINITIONS
from localgames.protocol import ClientMessage, JsonLineChannel, ServerMessage, build_message
from localgames.server.lobby import Lobby, LobbyError, Player


class GameServer:
    """Accepts TCP clients and routes their messages to the lobby."""

    def __init__(
        self,
        lobby: Lobby,
        port: int = SERVER_PORT,
        discovery_port: Optional[int] = DISCOVERY_PORT,
    ) -> None:
        self._lobby = lobby
        self._requested_port = port
        self._discovery_port = discovery_port
        self._listener: Optional[socket.socket] = None
        self._stopped = threading.Event()
        self._discovery: Optional[DiscoveryResponder] = None
        self._handlers: Dict[str, Callable[[Player, dict], None]] = {
            ClientMessage.JOIN: lambda player, message: lobby.join(player, message.get("game")),
            ClientMessage.LEAVE: lambda player, message: lobby.leave(player),
            ClientMessage.MOVE: lambda player, message: lobby.play(player, message.get("move")),
        }

    @property
    def port(self) -> int:
        return self._listener.getsockname()[1]

    @property
    def player_count(self) -> int:
        return self._lobby.player_count

    def start(self) -> None:
        """Binds the ports and serves in background threads. Raises OSError if they are taken."""
        if self._discovery_port is not None:
            self._discovery = DiscoveryResponder(self._discovery_port)
        try:
            self._listener = self._open_listener()
        except OSError:
            if self._discovery:
                self._discovery.close()
            raise
        if self._discovery:
            self._discovery.start(self.port)
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._tick_loop, daemon=True).start()

    def close(self) -> None:
        self._stopped.set()
        if self._listener:
            self._listener.close()
        if self._discovery:
            self._discovery.close()

    def _open_listener(self) -> socket.socket:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name != "nt":  # on Windows SO_REUSEADDR would allow two servers on one port
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("", self._requested_port))
            listener.listen()
        except OSError:
            listener.close()
            raise
        return listener

    def _accept_loop(self) -> None:
        while True:
            try:
                client, _ = self._listener.accept()
            except OSError:
                return
            threading.Thread(target=self._serve_client, args=(client,), daemon=True).start()

    def _tick_loop(self) -> None:
        while not self._stopped.wait(TICK_INTERVAL_SECONDS):
            self._lobby.tick()

    def _serve_client(self, client: socket.socket) -> None:
        channel = JsonLineChannel(client)
        player: Optional[Player] = None
        try:
            player = self._greet(channel)
            while player is not None and (message := channel.receive()) is not None:
                self._dispatch(player, message)
        except (OSError, ValueError):
            pass
        finally:
            if player is not None:
                self._lobby.unregister(player)
            channel.close()

    def _greet(self, channel: JsonLineChannel) -> Optional[Player]:
        hello = channel.receive()
        if hello is None or hello.get("type") != ClientMessage.HELLO:
            return None
        player = Player(str(hello.get("name", "")).strip(), channel)
        try:
            self._lobby.register(player)
        except LobbyError as error:
            channel.send(build_message(ServerMessage.ERROR, message=str(error)))
            return None
        return player

    def _dispatch(self, player: Player, message: dict) -> None:
        handler = self._handlers.get(message.get("type"))
        if handler is None:
            return
        try:
            handler(player, message)
        except (LobbyError, InvalidMove) as error:
            player.send(build_message(ServerMessage.ERROR, message=str(error)))


def create_server(port: int = SERVER_PORT, discovery_port: Optional[int] = DISCOVERY_PORT) -> GameServer:
    return GameServer(Lobby(GAME_DEFINITIONS), port, discovery_port)
