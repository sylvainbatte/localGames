import unittest

from localgames.games.base import InvalidMove
from localgames.games.registry import GAME_DEFINITIONS
from localgames.protocol import ServerMessage
from localgames.server.lobby import Lobby, LobbyError, Player

GAME_ID = GAME_DEFINITIONS[0].id


class FakeChannel:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def types(self):
        return [message["type"] for message in self.sent]


def connect(lobby, name):
    channel = FakeChannel()
    player = Player(name, channel)
    lobby.register(player)
    return player, channel


class LobbyTest(unittest.TestCase):
    def setUp(self):
        self.lobby = Lobby(GAME_DEFINITIONS)

    def test_rejects_duplicate_and_invalid_names(self):
        connect(self.lobby, "alice")
        for name in ("alice", "", "x" * 50):
            with self.subTest(name=name), self.assertRaises(LobbyError):
                self.lobby.register(Player(name, FakeChannel()))

    def test_waiting_player_is_visible_to_everyone(self):
        alice, _ = connect(self.lobby, "alice")
        _, bob_channel = connect(self.lobby, "bob")
        self.lobby.join(alice, GAME_ID)

        snapshot = [m for m in bob_channel.sent if m["type"] == ServerMessage.LOBBY][-1]
        self.assertEqual(snapshot["games"][0]["waiting"], ["alice"])

    def test_game_starts_when_enough_players_joined(self):
        alice, alice_channel = connect(self.lobby, "alice")
        bob, bob_channel = connect(self.lobby, "bob")
        self.lobby.join(alice, GAME_ID)
        self.assertNotIn(ServerMessage.GAME_START, alice_channel.types())
        self.lobby.join(bob, GAME_ID)

        start = [m for m in alice_channel.sent if m["type"] == ServerMessage.GAME_START][0]
        self.assertEqual(start["players"], ["alice", "bob"])
        self.assertEqual(start["you"], 0)
        self.assertIn(ServerMessage.GAME_START, bob_channel.types())

    def test_leaving_removes_player_from_queue(self):
        alice, _ = connect(self.lobby, "alice")
        bob, bob_channel = connect(self.lobby, "bob")
        self.lobby.join(alice, GAME_ID)
        self.lobby.leave(alice)
        self.lobby.join(bob, GAME_ID)
        self.assertNotIn(ServerMessage.GAME_START, bob_channel.types())

    def test_moves_are_relayed_and_invalid_moves_raise(self):
        alice, alice_channel = connect(self.lobby, "alice")
        bob, bob_channel = connect(self.lobby, "bob")
        self.lobby.join(alice, GAME_ID)
        self.lobby.join(bob, GAME_ID)

        self.lobby.play(alice, {"cell": 0})
        self.assertIn(ServerMessage.GAME_UPDATE, bob_channel.types())
        with self.assertRaises(InvalidMove):
            self.lobby.play(alice, {"cell": 1})

    def test_disconnect_notifies_opponent_and_frees_them(self):
        alice, _ = connect(self.lobby, "alice")
        bob, bob_channel = connect(self.lobby, "bob")
        self.lobby.join(alice, GAME_ID)
        self.lobby.join(bob, GAME_ID)

        self.lobby.unregister(alice)

        self.assertIn(ServerMessage.OPPONENT_LEFT, bob_channel.types())
        self.assertIsNone(bob.session)

    def test_cannot_play_without_a_match(self):
        alice, _ = connect(self.lobby, "alice")
        with self.assertRaises(LobbyError):
            self.lobby.play(alice, {"cell": 0})


if __name__ == "__main__":
    unittest.main()
