"""UDP discovery so clients can find a server on the local network without typing an IP."""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Optional, Tuple

from localgames.config import DISCOVERY_PORT, DISCOVERY_TIMEOUT_SECONDS

Address = Tuple[str, int]

_REQUEST = b"LOCALGAMES?"
_SERVICE_NAME = "localgames"


class DiscoveryResponder:
    """Answers discovery requests with the TCP port of the game server.

    Binding is exclusive on purpose: failing to bind means another server
    already runs on this machine.
    """

    def __init__(self, discovery_port: int) -> None:
        self._reply = b""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._sock.bind(("", discovery_port))
        except OSError:
            self._sock.close()
            raise

    def start(self, server_port: int) -> None:
        self._reply = json.dumps({"service": _SERVICE_NAME, "port": server_port}).encode()
        threading.Thread(target=self._serve, daemon=True).start()

    def close(self) -> None:
        self._sock.close()

    def _serve(self) -> None:
        while True:
            try:
                data, sender = self._sock.recvfrom(256)
                if data == _REQUEST:
                    self._sock.sendto(self._reply, sender)
            except OSError:
                return


def find_server(
    discovery_port: int = DISCOVERY_PORT,
    timeout: float = DISCOVERY_TIMEOUT_SECONDS,
) -> Optional[Address]:
    """Broadcasts a discovery request and returns the first server that answers."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in ("255.255.255.255", "127.0.0.1"):
            try:
                sock.sendto(_REQUEST, (target, discovery_port))
            except OSError:
                continue
        return _await_reply(sock, timeout)


def _await_reply(sock: socket.socket, timeout: float) -> Optional[Address]:
    deadline = time.monotonic() + timeout
    while (remaining := deadline - time.monotonic()) > 0:
        sock.settimeout(remaining)
        try:
            data, (host, _) = sock.recvfrom(256)
            reply = json.loads(data)
            if reply.get("service") == _SERVICE_NAME:
                return host, int(reply["port"])
        except socket.timeout:
            return None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return None
