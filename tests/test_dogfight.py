import random
import unittest

from localgames.games.base import DIFFICULTIES, HARD, InvalidMove
from localgames.games.dogfight.bot import DogfightBot
from localgames.games.dogfight.logic import (
    HEIGHT, MAX_ROW, MIN_ROW, PLANE_COLUMNS, RELOAD_TICKS, ROUND_DELAY_TICKS, WIN_SCORE, Dogfight,
)
from localgames.games.dogfight.view import DogfightView


def started_game():
    game = Dogfight()
    game._countdown = 0
    return game


def run(game, ticks):
    for _ in range(ticks):
        game.tick()


class _Always(random.Random):
    def random(self):
        return 0.0


class DogfightTest(unittest.TestCase):
    def test_nothing_flies_during_the_start_delay(self):
        game = Dogfight()
        game.play(0, {"fire": True})
        self.assertEqual(game.state()["missiles"], [])

    def test_planes_move_and_are_clamped(self):
        game = started_game()
        start = game.state()["planes"][0]
        game.play(0, {"move": -1})
        self.assertEqual(game.state()["planes"], [start - 1, start])
        for _ in range(30):
            game.play(0, {"move": -1})
            game.play(1, {"move": 1})
        self.assertEqual(game.state()["planes"], [MIN_ROW, MAX_ROW])

    def test_rejects_malformed_moves(self):
        game = started_game()
        for move in (None, "up", {}, {"move": 0}, {"move": True}, {"move": "1"}, {"fire": False}):
            with self.assertRaises(InvalidMove, msg=repr(move)):
                game.play(0, move)

    def test_fire_spawns_a_missile_and_reloads(self):
        game = started_game()
        game.play(0, {"fire": True})
        game.play(0, {"fire": True})  # still reloading: ignored
        self.assertEqual(len(game.state()["missiles"]), 1)
        self.assertEqual(game.state()["cooldowns"][0], RELOAD_TICKS)
        run(game, RELOAD_TICKS)
        game.play(0, {"fire": True})
        self.assertEqual(len(game.state()["missiles"]), 2)

    def test_missile_on_the_enemy_row_scores(self):
        game = started_game()
        game.play(0, {"fire": True})
        run(game, 60)
        state = game.state()
        self.assertEqual(state["scores"], [1, 0])
        self.assertEqual(state["missiles"], [])
        self.assertGreater(state["countdown"], 0)
        self.assertLessEqual(state["countdown"], ROUND_DELAY_TICKS)
        self.assertEqual(state["explosions"], [[PLANE_COLUMNS[1], HEIGHT // 2]])

    def test_missile_hits_within_the_plane_height_only(self):
        game = started_game()
        game.play(1, {"move": 1})
        game.play(1, {"move": 1})  # two rows away from the missile: it flies past
        game.play(0, {"fire": True})
        run(game, 60)
        self.assertEqual(game.state()["scores"], [0, 0])
        self.assertEqual(game.state()["missiles"], [])

    def test_missiles_crossing_each_other_cancel_out(self):
        game = started_game()
        game.play(0, {"fire": True})
        game.play(1, {"fire": True})
        run(game, 60)
        self.assertEqual(game.state()["scores"], [0, 0])
        self.assertEqual(game.state()["missiles"], [])

    def test_round_reset_recenters_planes(self):
        game = started_game()
        game.play(1, {"move": 1})
        game.play(0, {"fire": True})
        game.play(1, {"move": -1})
        run(game, 60)
        self.assertEqual(game.state()["planes"], [HEIGHT // 2] * 2)

    def test_first_to_win_score_wins(self):
        game = started_game()
        for _ in range(WIN_SCORE):
            game._countdown = 0
            game.play(0, {"fire": True})
            run(game, 60)
        state = game.state()
        self.assertEqual((state["winner"], state["over"]), (0, True))
        with self.assertRaises(InvalidMove):
            game.play(0, {"fire": True})

    def test_simultaneous_hits_at_match_point_play_on(self):
        game = started_game()
        game._scores = [WIN_SCORE - 1, WIN_SCORE - 1]
        game._end_round([[0, 3, 8], [1, 56, 8]])
        self.assertIsNone(game.state()["winner"])
        self.assertEqual(game.state()["scores"], [WIN_SCORE, WIN_SCORE])


class DogfightBotTest(unittest.TestCase):
    def test_hard_bot_fires_when_aligned(self):
        game = started_game()
        bot = DogfightBot(0, HARD)
        moves = [bot.choose_move(game.state()) for _ in range(4)]
        self.assertIn({"fire": True}, moves)

    def test_hard_bot_dodges_incoming_missile(self):
        game = started_game()
        game.play(0, {"fire": True})
        game.tick()
        bot = DogfightBot(1, HARD, _Always())
        moves = [bot.choose_move(game.state()) for _ in range(2)]
        self.assertTrue(any(m and "move" in m for m in moves))

    def test_bots_finish_a_match_against_each_other(self):
        for difficulty in DIFFICULTIES:
            game = started_game()
            bots = [DogfightBot(0, difficulty, random.Random(1)), DogfightBot(1, difficulty, random.Random(2))]
            for _ in range(20000):
                if game.is_over:
                    break
                for bot in bots:
                    move = bot.choose_move(game.state())
                    if move:
                        game.play(bot.my_index, move)
                game.tick()
            self.assertTrue(game.is_over, difficulty)


class DogfightViewTest(unittest.TestCase):
    def test_renders_and_maps_keys(self):
        view = DogfightView(0, ["a", "b"])
        game = started_game()
        game.play(0, {"fire": True})
        lines = view.render(game.state())
        self.assertGreater(len(lines), HEIGHT)
        self.assertEqual(view.on_key(" ", game.state()), {"fire": True})
        self.assertEqual(view.on_key("UP", game.state()), {"move": -1})
        self.assertEqual(view.on_key("s", game.state()), {"move": 1})
        self.assertIsNone(view.on_key("x", game.state()))
