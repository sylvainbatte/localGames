"""Finds the game server, starting a detached one if nobody hosts yet."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Optional

from localgames.config import SERVER_PORT
from localgames.discovery import Address, find_server

SERVER_IDLE_TIMEOUT_SECONDS = 60
_STARTUP_ATTEMPTS = 10
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ServerLocator:
    def __init__(self, host: Optional[str] = None, port: int = SERVER_PORT) -> None:
        self._host = host
        self._port = port

    def locate(self) -> Optional[Address]:
        """Returns the server address, hosting a server on this machine if none answers."""
        if self._host:
            return self._host, self._port
        address = find_server()
        if address is not None:
            return address
        self._spawn_detached_server()
        for _ in range(_STARTUP_ATTEMPTS):
            address = find_server()
            if address is not None:
                return address
            time.sleep(0.2)
        return None

    def _spawn_detached_server(self) -> None:
        command = [
            sys.executable, "-m", "localgames", "--server",
            "--port", str(self._port), "--idle-timeout", str(SERVER_IDLE_TIMEOUT_SECONDS),
        ]
        options = {
            "cwd": _PROJECT_ROOT,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            options["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        subprocess.Popen(command, **options)
