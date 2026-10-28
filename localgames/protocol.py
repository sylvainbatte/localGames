"""Wire protocol: newline-delimited JSON messages over TCP."""

from __future__ import annotations

import json
import socket
import threading
from typing import Optional

MAX_LINE_BYTES = 65536


class ClientMessage:
    HELLO = "hello"
    JOIN = "join"
    LEAVE = "leave"
    MOVE = "move"


class ServerMessage:
    WELCOME = "welcome"
    ERROR = "error"
    LOBBY = "lobby"
    GAME_START = "game_start"
    GAME_UPDATE = "game_update"
    OPPONENT_LEFT = "opponent_left"


def build_message(message_type: str, **fields) -> dict:
    return {"type": message_type, **fields}


class JsonLineChannel:
    """Sends and receives JSON objects, one per line, over a connected socket."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._reader = sock.makefile("rb")
        self._send_lock = threading.Lock()

    def send(self, message: dict) -> None:
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        with self._send_lock:
            self._sock.sendall(data)

    def receive(self) -> Optional[dict]:
        """Blocks until a message arrives; returns None once the peer disconnects."""
        line = self._reader.readline(MAX_LINE_BYTES)
        if not line:
            return None
        message = json.loads(line)
        if not isinstance(message, dict):
            raise ValueError("A message must be a JSON object")
        return message

    def close(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()
