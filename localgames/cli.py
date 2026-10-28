from __future__ import annotations

import argparse
import time
from typing import List, Optional

from localgames.client.app import App
from localgames.client.locator import SERVER_IDLE_TIMEOUT_SECONDS, ServerLocator
from localgames.client.terminal import Terminal
from localgames.config import SERVER_PORT
from localgames.server.server import create_server


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_arguments(argv)
    if args.server:
        return _run_dedicated_server(args.port, args.idle_timeout)
    return _run_client(args)


def _parse_arguments(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="localgames", description="Jeux à deux sur réseau local.")
    parser.add_argument("--name", default="", help="pseudo pré-rempli")
    parser.add_argument("--host", help="adresse IP du serveur (si la détection automatique échoue)")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="port TCP du serveur")
    parser.add_argument("--server", action="store_true", help="lance uniquement un serveur dédié")
    parser.add_argument(
        "--idle-timeout", type=float, default=SERVER_IDLE_TIMEOUT_SECONDS,
        help="avec --server : s'arrête après ce nombre de secondes sans aucun joueur (0 : jamais)",
    )
    return parser.parse_args(argv)


def _run_dedicated_server(port: int, idle_timeout: float) -> int:
    server = create_server(port=port)
    try:
        server.start()
    except OSError as error:
        print(f"Impossible de démarrer le serveur : {error}")
        return 1
    print(f"Serveur LocalGames en écoute sur le port {server.port}. Ctrl+C pour arrêter.")
    try:
        _wait_until_idle(server, idle_timeout)
    except KeyboardInterrupt:
        pass
    server.close()
    return 0


def _wait_until_idle(server, idle_timeout: float) -> None:
    """Blocks forever, or until no player has been connected for idle_timeout seconds."""
    idle_since = time.monotonic()
    while True:
        time.sleep(1)
        if server.player_count > 0:
            idle_since = time.monotonic()
        elif idle_timeout and time.monotonic() - idle_since >= idle_timeout:
            return


def _run_client(args: argparse.Namespace) -> int:
    locator = ServerLocator(host=args.host, port=args.port)
    try:
        with Terminal() as terminal:
            App(terminal, locator, initial_name=args.name).run()
    except KeyboardInterrupt:
        pass
    return 0
