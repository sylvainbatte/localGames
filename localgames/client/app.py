"""The client: login, game menu and match screens driven by one event loop."""

from __future__ import annotations

import queue
import socket
import threading
from typing import List, Optional

from localgames.ansi import BOLD, CYAN, DIM, GREEN, RED, REVERSE, YELLOW, style
from localgames.client.locator import ServerLocator
from localgames.client.terminal import Terminal
from localgames.config import CONNECT_TIMEOUT_SECONDS, MAX_NAME_LENGTH
from localgames.games.base import EASY, HARD, MEDIUM, GameView
from localgames.games.registry import get_definition
from localgames.protocol import ClientMessage, JsonLineChannel, ServerMessage, build_message

POLL_SECONDS = 0.05
_DISCONNECTED = {"type": "disconnected"}
_BOT_KEYS = {"1": EASY, "2": MEDIUM, "3": HARD}


class App:
    def __init__(self, terminal: Terminal, locator: ServerLocator, initial_name: str = "") -> None:
        self._terminal = terminal
        self._locator = locator
        self._name = initial_name[:MAX_NAME_LENGTH]
        self._channel: Optional[JsonLineChannel] = None
        self._incoming: "queue.Queue[dict]" = queue.Queue()
        self._lobby: dict = {"online": [], "games": []}
        self._cursor = 0
        self._notice = ""
        self._view: Optional[GameView] = None
        self._state: dict = {}
        self._result_shown = False

    def run(self) -> None:
        while self._login():
            quit_requested = self._lobby_loop()
            self._close_connection()
            if quit_requested:
                return

    # --- login -------------------------------------------------------------------------------

    def _login(self) -> bool:
        """Asks for a name and connects. Returns False when the user quits."""
        while True:
            if not self._ask_name():
                return False
            if self._connect():
                return True

    def _ask_name(self) -> bool:
        while True:
            self._terminal.draw([
                style("LocalGames", BOLD, CYAN), "",
                f"Pseudo : {self._name}█", "",
                self._notice,
                style("Entrée valider · Échap quitter", DIM),
            ])
            key = self._terminal.read_key(1)
            if key == "ESC":
                return False
            if key == "ENTER" and self._name.strip():
                self._name = self._name.strip()
                return True
            if key == "BACKSPACE":
                self._name = self._name[:-1]
            elif key and len(key) == 1 and key.isprintable() and len(self._name) < MAX_NAME_LENGTH:
                self._name += key

    def _connect(self) -> bool:
        self._terminal.draw(["Recherche du serveur…"])
        address = self._locator.locate()
        if address is None:
            self._notice = style("Serveur introuvable (essaie --host IP).", RED)
            return False
        try:
            sock = socket.create_connection(address, timeout=CONNECT_TIMEOUT_SECONDS)
        except OSError as error:
            self._notice = style(f"Connexion impossible : {error}", RED)
            return False
        sock.settimeout(None)
        self._channel = JsonLineChannel(sock)
        self._incoming = queue.Queue()
        threading.Thread(target=self._read_loop, args=(self._channel, self._incoming), daemon=True).start()
        self._channel.send(build_message(ClientMessage.HELLO, name=self._name))
        reply = self._incoming.get()
        if reply["type"] != ServerMessage.WELCOME:
            self._notice = style(reply.get("message", "Connexion refusée."), RED)
            self._close_connection()
            return False
        self._notice = ""
        return True

    @staticmethod
    def _read_loop(channel: JsonLineChannel, messages: "queue.Queue[dict]") -> None:
        try:
            while (message := channel.receive()) is not None:
                messages.put(message)
        except (OSError, ValueError):
            pass
        messages.put(_DISCONNECTED)

    def _close_connection(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
        self._view = None

    # --- main loop ---------------------------------------------------------------------------

    def _lobby_loop(self) -> bool:
        """Runs until the user quits (returns True) or the connection drops (returns False)."""
        while True:
            if not self._handle_messages():
                self._notice = style("Connexion au serveur perdue.", RED)
                return False
            self._draw()
            key = self._terminal.read_key(POLL_SECONDS)
            if key is not None and self._handle_key(key):
                return True

    def _handle_messages(self) -> bool:
        while True:
            try:
                message = self._incoming.get_nowait()
            except queue.Empty:
                return True
            kind = message["type"]
            if kind == _DISCONNECTED["type"]:
                return False
            if kind == ServerMessage.LOBBY:
                self._lobby = message
            elif kind == ServerMessage.GAME_START:
                self._start_match(message)
            elif kind == ServerMessage.GAME_UPDATE:
                self._state = message["state"]
            elif kind == ServerMessage.OPPONENT_LEFT:
                self._view = None
                self._notice = style(f"{message['name']} a quitté la partie.", YELLOW)
            elif kind == ServerMessage.ERROR:
                self._notice = style(message.get("message", "Erreur."), RED)

    def _start_match(self, message: dict) -> None:
        definition = get_definition(message["game"])
        self._view = definition.create_view(message["you"], message["players"])
        self._state = message["state"]
        self._notice = ""

    def _handle_key(self, key: str) -> bool:
        """Returns True when the user asked to quit."""
        if self._view is not None:
            return self._handle_match_key(key)
        games = self._lobby["games"]
        if key == "ESC":
            return True
        if not games:
            return False
        if key == "UP":
            self._cursor = (self._cursor - 1) % len(games)
        elif key == "DOWN":
            self._cursor = (self._cursor + 1) % len(games)
        elif key == "ENTER":
            self._notice = ""
            self._send(ClientMessage.JOIN, game=games[self._cursor]["id"])
        elif key == " ":
            self._send(ClientMessage.LEAVE)
        elif key in _BOT_KEYS and self._waiting_game_id() is not None:
            self._send(ClientMessage.JOIN_BOT, game=self._waiting_game_id(), difficulty=_BOT_KEYS[key])
        return False

    def _handle_match_key(self, key: str) -> bool:
        if key == "ESC":
            self._send(ClientMessage.LEAVE)
            self._view = None
            return False
        if self._state.get("over") and key == "ENTER":
            self._view = None
            return False
        move = self._view.on_key(key, self._state)
        if move is not None:
            self._send(ClientMessage.MOVE, move=move)
        return False

    def _send(self, message_type: str, **fields) -> None:
        try:
            self._channel.send(build_message(message_type, **fields))
        except OSError:
            pass  # the reader thread reports the disconnect

    # --- drawing -----------------------------------------------------------------------------

    def _draw(self) -> None:
        lines = self._match_lines() if self._view is not None else self._menu_lines()
        self._terminal.draw(lines)

    def _match_lines(self) -> List[str]:
        lines = self._view.render(self._state)
        footer = "Entrée : retour au menu" if self._state.get("over") else self._view.controls
        return lines + ["", style(footer, DIM)]

    def _menu_lines(self) -> List[str]:
        waiting_for = self._waiting_game_id()
        lines = [style(f"LocalGames — {self._name}", BOLD, CYAN), ""]
        for index, game in enumerate(self._lobby["games"]):
            others = [name for name in game["waiting"] if name != self._name]
            detail = f"en attente : {', '.join(others)}" if others else "personne n'attend"
            if game["id"] == waiting_for:
                detail = style("en attente d'un adversaire…", YELLOW)
            line = f"  {game['name']:<14} {detail}  ({game['playing']} en jeu)"
            lines.append(style(line, REVERSE) if index == self._cursor else line)
        lines += ["", f"En ligne : {', '.join(self._lobby['online']) or '-'}", ""]
        if self._notice:
            lines += [self._notice, ""]
        lines.append(style("↑↓ choisir · Entrée jouer · Espace annuler l'attente · 1/2/3 ordinateur facile/moyen/difficile · Échap quitter", DIM))
        return lines

    def _waiting_game_id(self) -> Optional[str]:
        for game in self._lobby["games"]:
            if self._name in game["waiting"]:
                return game["id"]
        return None
