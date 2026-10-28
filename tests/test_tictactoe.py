import unittest

from localgames.games.base import InvalidMove
from localgames.games.tictactoe.logic import TicTacToe


def play_cells(game, cells):
    for turn, cell in enumerate(cells):
        game.play(turn % 2, {"cell": cell})


class TicTacToeTest(unittest.TestCase):
    def test_first_player_starts_and_players_alternate(self):
        game = TicTacToe()
        game.play(0, {"cell": 0})
        self.assertEqual(game.state()["turn"], 1)

    def test_rejects_move_out_of_turn(self):
        with self.assertRaises(InvalidMove):
            TicTacToe().play(1, {"cell": 0})

    def test_rejects_occupied_cell(self):
        game = TicTacToe()
        game.play(0, {"cell": 4})
        with self.assertRaises(InvalidMove):
            game.play(1, {"cell": 4})

    def test_rejects_malformed_moves(self):
        game = TicTacToe()
        for move in (None, "4", {}, {"cell": "1"}, {"cell": 9}, {"cell": -1}, {"cell": True}):
            with self.subTest(move=move), self.assertRaises(InvalidMove):
                game.play(0, move)

    def test_detects_a_win_and_exposes_the_line(self):
        game = TicTacToe()
        play_cells(game, [0, 3, 1, 4, 2])
        state = game.state()
        self.assertTrue(state["over"])
        self.assertEqual(state["winner"], 0)
        self.assertEqual(state["line"], [0, 1, 2])

    def test_detects_a_draw(self):
        game = TicTacToe()
        play_cells(game, [0, 1, 2, 4, 3, 5, 7, 6, 8])
        state = game.state()
        self.assertTrue(state["over"])
        self.assertTrue(state["draw"])
        self.assertIsNone(state["winner"])

    def test_rejects_moves_after_the_game_is_over(self):
        game = TicTacToe()
        play_cells(game, [0, 3, 1, 4, 2])
        with self.assertRaises(InvalidMove):
            game.play(1, {"cell": 8})


if __name__ == "__main__":
    unittest.main()
