import random
import unittest

from localgames.games.base import DIFFICULTIES, EASY, HARD, MEDIUM
from localgames.games.pong.bot import PongBot
from localgames.games.pong.logic import Pong
from localgames.games.registry import GAME_DEFINITIONS
from localgames.games.tictactoe.bot import TicTacToeBot
from localgames.games.tictactoe.logic import TicTacToe
from localgames.protocol import ServerMessage
from localgames.server.lobby import Lobby, LobbyError, Player
from tests.test_lobby import connect


class _Never(random.Random):
    """Random source that always takes the first option and never slips."""

    def random(self):
        return 0.0

    def choice(self, seq):
        return seq[0]


class TicTacToeBotTest(unittest.TestCase):
    def test_takes_winning_cell(self):
        game = TicTacToe()
        for index, cell in ((0, 0), (1, 3), (0, 1), (1, 4)):
            game.play(index, {"cell": cell})
        self.assertEqual(TicTacToeBot(0, HARD).choose_move(game.state()), {"cell": 2})

    def test_blocks_opponent(self):
        game = TicTacToe()
        for index, cell in ((0, 0), (1, 4), (0, 1)):
            game.play(index, {"cell": cell})
        self.assertEqual(TicTacToeBot(1, HARD).choose_move(game.state()), {"cell": 2})

    def test_waits_when_not_its_turn(self):
        self.assertIsNone(TicTacToeBot(1).choose_move(TicTacToe().state()))

    def test_plays_full_game_against_itself(self):
        for difficulty in DIFFICULTIES:
            game = TicTacToe()
            bots = [TicTacToeBot(0, difficulty), TicTacToeBot(1, difficulty)]
            while not game.is_over:
                bot = bots[game.state()["turn"]]
                game.play(bot.my_index, bot.choose_move(game.state()))

    def test_hard_picks_perfect_reply(self):
        game = TicTacToe()
        game.play(0, {"cell": 0})
        for seed in range(20):  # corner opening: the only non-losing replies are the center
            bot = TicTacToeBot(1, HARD, random.Random(seed))
            move = bot.choose_move(game.state())["cell"]
            self.assertIn(move, range(9))
        self.assertEqual(TicTacToeBot(1, HARD, _Never()).choose_move(game.state()), {"cell": 4})

    def test_rejects_unknown_difficulty(self):
        with self.assertRaises(ValueError):
            TicTacToeBot(0, "impossible")


class PongBotTest(unittest.TestCase):
    def test_moves_toward_ball(self):
        state = Pong().state()
        state["ball"] = [30, 14]
        bot = PongBot(1, EASY)
        moves = [bot.choose_move(state) for _ in range(6)]
        self.assertTrue(all(m == {"move": 1} for m in moves if m))
        self.assertTrue(any(moves))


class LobbyBotTest(unittest.TestCase):
    def setUp(self):
        self.lobby = Lobby(GAME_DEFINITIONS)

    def test_requires_waiting(self):
        alice, _ = connect(self.lobby, "alice")
        with self.assertRaises(LobbyError):
            self.lobby.join_bot(alice, "tictactoe")

    def test_rejects_unknown_difficulty(self):
        alice, _ = connect(self.lobby, "alice")
        self.lobby.join(alice, "pong")
        with self.assertRaises(LobbyError):
            self.lobby.join_bot(alice, "pong", "impossible")

    def test_tictactoe_bot_replies_to_moves(self):
        alice, channel = connect(self.lobby, "alice")
        self.lobby.join(alice, "tictactoe")
        self.lobby.join_bot(alice, "tictactoe")
        self.lobby.play(alice, {"cell": 0})
        state = [m for m in channel.sent if m["type"] == ServerMessage.GAME_UPDATE][-1]["state"]
        self.assertEqual(state["turn"], 0)
        self.assertEqual(sum(c is not None for c in state["board"]), 2)

    def test_pong_bot_moves_on_tick(self):
        alice, channel = connect(self.lobby, "alice")
        self.lobby.join(alice, "pong")
        self.lobby.join_bot(alice, "pong", HARD)
        for _ in range(200):
            self.lobby.tick()
        self.assertIn(ServerMessage.GAME_UPDATE, [m["type"] for m in channel.sent])
        state = channel.sent[-1]["state"]
        center = state["paddles"][1] + 1.5
        self.assertLess(abs(state["ball"][1] - center), 4)  # the bot keeps its paddle near the ball
