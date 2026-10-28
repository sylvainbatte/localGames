import random
import unittest

from localgames.games.base import InvalidMove
from localgames.games.pong.logic import (
    HEIGHT, PADDLE_COLUMNS, PADDLE_HEIGHT, PADDLE_STEP, SERVE_DELAY_TICKS, WIDTH, WIN_SCORE, Pong,
)


def started_game(toward=0):
    game = Pong(random.Random(1))
    game._prepare_serve(toward)
    game._serve_countdown = 0
    return game


class PongTest(unittest.TestCase):
    def test_ball_waits_for_the_serve_delay(self):
        game = Pong(random.Random(1))
        before = game.state()["ball"]
        for _ in range(SERVE_DELAY_TICKS):
            game.tick()
        self.assertEqual(game.state()["ball"], before)
        game.tick()
        self.assertNotEqual(game.state()["ball"], before)

    def test_move_shifts_only_the_senders_paddle_and_is_clamped(self):
        game = Pong(random.Random(1))
        start = game.state()["paddles"][0]
        game.play(0, {"move": 1})
        self.assertEqual(game.state()["paddles"], [start + PADDLE_STEP, start])
        for _ in range(20):
            game.play(0, {"move": 1})
            game.play(1, {"move": -1})
        self.assertEqual(game.state()["paddles"], [HEIGHT - PADDLE_HEIGHT, 0])

    def test_rejects_malformed_moves(self):
        game = Pong(random.Random(1))
        for move in (None, "up", {}, {"move": 0}, {"move": 2}, {"move": True}, {"move": "1"}):
            with self.assertRaises(InvalidMove, msg=repr(move)):
                game.play(0, move)

    def test_paddle_returns_the_ball(self):
        game = started_game(toward=0)
        game._ball = [4.0, HEIGHT / 2]
        game._velocity = [-0.7, 0.0]
        game._paddles[0] = int(HEIGHT / 2) - 1
        for _ in range(5):
            game.tick()
        self.assertGreater(game._velocity[0], 0)
        self.assertEqual(game.state()["scores"], [0, 0])

    def test_missed_ball_scores_for_the_opponent_and_serves_back(self):
        game = started_game(toward=0)
        game._ball = [4.0, HEIGHT - 1.0]
        game._velocity = [-1.0, 0.0]
        game._paddles[0] = 0
        for _ in range(10):
            game.tick()
        state = game.state()
        self.assertEqual(state["scores"], [0, 1])
        self.assertGreater(state["serve_countdown"], 0)
        self.assertLess(game._velocity[0], 0)  # served toward the player who conceded

    def test_ball_bounces_on_walls(self):
        game = started_game()
        game._ball = [WIDTH / 2, 0.2]
        game._velocity = [0.1, -0.5]
        game.tick()
        self.assertGreater(game._velocity[1], 0)
        self.assertGreaterEqual(game.state()["ball"][1], 0)

    def test_first_to_win_score_ends_the_game(self):
        game = started_game()
        for _ in range(WIN_SCORE):
            game._ball = [WIDTH - 1.5, 0.0]
            game._velocity = [1.0, 0.0]
            game._serve_countdown = 0
            game._paddles[1] = HEIGHT - PADDLE_HEIGHT
            game.tick()
        state = game.state()
        self.assertTrue(state["over"])
        self.assertEqual(state["winner"], 0)
        with self.assertRaises(InvalidMove):
            game.play(0, {"move": 1})

    def test_paddle_columns_are_inside_the_field(self):
        self.assertTrue(all(0 < column < WIDTH - 1 for column in PADDLE_COLUMNS))


class PongSessionTest(unittest.TestCase):
    def test_lobby_tick_broadcasts_state_to_both_players(self):
        from localgames.games.registry import get_definition
        from localgames.server.lobby import Lobby, Player

        class Recorder:
            def __init__(self):
                self.messages = []

            def send(self, message):
                self.messages.append(message)

        lobby = Lobby([get_definition("pong")])
        channels = [Recorder(), Recorder()]
        for name, channel in zip(("a", "b"), channels):
            player = Player(name, channel)
            lobby.register(player)
            lobby.join(player, "pong")
        lobby.tick()
        for channel in channels:
            self.assertEqual(channel.messages[-1]["type"], "game_update")
