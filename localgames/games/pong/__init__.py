from localgames.games.base import GameDefinition
from localgames.games.pong.logic import Pong
from localgames.games.pong.view import PongView

PONG = GameDefinition(
    id="pong",
    name="Pong",
    player_count=2,
    create_game=Pong,
    create_view=PongView,
)
