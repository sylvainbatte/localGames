from localgames.games.base import GameDefinition
from localgames.games.tictactoe.bot import TicTacToeBot
from localgames.games.tictactoe.logic import TicTacToe
from localgames.games.tictactoe.view import TicTacToeView

TIC_TAC_TOE = GameDefinition(
    id="tictactoe",
    name="Morpion",
    player_count=2,
    create_game=TicTacToe,
    create_view=TicTacToeView,
    create_bot=TicTacToeBot,
)
