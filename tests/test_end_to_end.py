import socket
import unittest

from localgames.discovery import find_server
from localgames.games.registry import GAME_DEFINITIONS
from localgames.protocol import ClientMessage, JsonLineChannel, ServerMessage, build_message
from localgames.server.server import create_server

GAME_ID = GAME_DEFINITIONS[0].id


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.discovery_port = free_udp_port()
        self.server = create_server(port=0, discovery_port=self.discovery_port)
        self.server.start()
        self.addCleanup(self.server.close)

    def connect(self, name):
        sock = socket.create_connection(("127.0.0.1", self.server.port), timeout=3)
        channel = JsonLineChannel(sock)
        self.addCleanup(channel.close)
        channel.send(build_message(ClientMessage.HELLO, name=name))
        return channel

    @staticmethod
    def receive_until(channel, message_type):
        while (message := channel.receive())["type"] != message_type:
            pass
        return message

    def wait_until_waiting(self, channel, name):
        while name not in self.receive_until(channel, ServerMessage.LOBBY)["games"][0]["waiting"]:
            pass

    def test_discovery_finds_the_server(self):
        address = find_server(discovery_port=self.discovery_port, timeout=2)
        self.assertIsNotNone(address)
        self.assertEqual(address[1], self.server.port)

    def test_second_server_cannot_share_the_discovery_port(self):
        with self.assertRaises(OSError):
            create_server(port=0, discovery_port=self.discovery_port).start()

    def test_two_players_play_a_full_game(self):
        alice, bob = self.connect("alice"), self.connect("bob")
        self.receive_until(alice, ServerMessage.WELCOME)
        self.receive_until(bob, ServerMessage.WELCOME)

        alice.send(build_message(ClientMessage.JOIN, game=GAME_ID))
        self.wait_until_waiting(bob, "alice")
        bob.send(build_message(ClientMessage.JOIN, game=GAME_ID))
        self.receive_until(alice, ServerMessage.GAME_START)
        self.receive_until(bob, ServerMessage.GAME_START)

        for player, cell in ((alice, 0), (bob, 3), (alice, 1), (bob, 4), (alice, 2)):
            player.send(build_message(ClientMessage.MOVE, move={"cell": cell}))
            updates = [self.receive_until(channel, ServerMessage.GAME_UPDATE) for channel in (alice, bob)]

        state = updates[1]
        self.assertTrue(state["state"]["over"])
        self.assertEqual(state["state"]["winner"], 0)

    def test_two_matches_run_simultaneously_and_independently(self):
        names = ["a1", "a2", "b1", "b2"]
        channels = {name: self.connect(name) for name in names}
        for channel in channels.values():
            self.receive_until(channel, ServerMessage.WELCOME)

        for first, second in (("a1", "a2"), ("b1", "b2")):
            channels[first].send(build_message(ClientMessage.JOIN, game=GAME_ID))
            self.wait_until_waiting(channels[first], first)
            channels[second].send(build_message(ClientMessage.JOIN, game=GAME_ID))
            self.receive_until(channels[second], ServerMessage.GAME_START)
        starts = {name: self.receive_until(channels[name], ServerMessage.GAME_START) for name in ("a1", "b1")}

        self.assertEqual(starts["a1"]["players"], ["a1", "a2"])
        self.assertEqual(starts["b1"]["players"], ["b1", "b2"])

        channels["a1"].send(build_message(ClientMessage.MOVE, move={"cell": 0}))
        self.receive_until(channels["a2"], ServerMessage.GAME_UPDATE)
        channels["b1"].send(build_message(ClientMessage.MOVE, move={"cell": 0}))  # same cell, other match
        update = self.receive_until(channels["b2"], ServerMessage.GAME_UPDATE)
        self.assertEqual(update["state"]["board"][0], 0)

    def test_duplicate_name_is_refused(self):
        first = self.connect("alice")
        self.receive_until(first, ServerMessage.WELCOME)
        second = self.connect("alice")
        self.assertEqual(second.receive()["type"], ServerMessage.ERROR)


if __name__ == "__main__":
    unittest.main()
