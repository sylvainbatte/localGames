from localgames.games.base import GameDefinition
from localgames.games.dogfight.bot import DogfightBot
from localgames.games.dogfight.logic import Dogfight
from localgames.games.dogfight.view import DogfightView

DOGFIGHT = GameDefinition(
    id="dogfight",
    name="Combat aérien",
    player_count=2,
    create_game=Dogfight,
    create_view=DogfightView,
    create_bot=DogfightBot,
)
