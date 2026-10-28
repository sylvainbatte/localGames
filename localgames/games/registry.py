"""The catalog of available games. Register new games here."""

from __future__ import annotations

from typing import Dict, Tuple

from localgames.games.base import GameDefinition
from localgames.games.pong import PONG
from localgames.games.tictactoe import TIC_TAC_TOE

GAME_DEFINITIONS: Tuple[GameDefinition, ...] = (
    TIC_TAC_TOE,
    PONG,
)

_BY_ID: Dict[str, GameDefinition] = {definition.id: definition for definition in GAME_DEFINITIONS}


def get_definition(game_id: str) -> GameDefinition:
    return _BY_ID[game_id]
