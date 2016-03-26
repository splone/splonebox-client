import socket
import unittest
import libnacl
import unittest.mock as mock
import struct
from threading import Thread

from splonecli.rpc.connection import Connection
from splonecli.rpc.crypto import CryptoState
from test import mocks


def collect_tests(suite: unittest.TestSuite):
    suite.addTest(ConnectionTest("test_connect"))
    suite.addTest(ConnectionTest("test_send_message"))
    suite.addTest(ConnectionTest("test_listen"))


class ConnectionTest(unittest.TestCase):
    def test_connect(self):
        con = Connection(libnacl.crypto_box_keypair()[0])
        mock_socket = mocks.connection_socket(con)

        con.connect("127.0.0.1", 6666, None, listen=False)
        mock_socket.connect.assert_called_with((socket.gethostbyname(
            "127.0.0.1"), 6666))

        some_callback = mock.Mock()
        listen_mock = mocks.Mock()
        con.listen = listen_mock
        con.connect("127.0.0.1", 6666, some_callback, listen=True)
        listen_mock.assert_called_with(some_callback, new_thread=True)

        mock_socket.connect.side_effect = ConnectionRefusedError
        with self.assertRaises(ConnectionRefusedError):
            con.connect("127.0.0.1", 6666, None, listen=False)

        with self.assertRaises(ConnectionError):
            con.connect(1, 1234, None, listen=False)

        with self.assertRaises(ConnectionError):
            con.connect("127.0.0.1", "bla", None, listen=False)

    def test_send_message(self):
        con = Connection(libnacl.crypto_box_keypair()[0])

        with self.assertRaises(BrokenPipeError):
            con.send_message(b'123')

    def test_listen(self):
        serverpk, serversk = libnacl.crypto_box_keypair()
        con = Connection(serverlongtermpk=serverpk)
        con.crypto_context.state = CryptoState.ESTABLISHED
        con._connected = True
        con.crypto_context.servershorttermpk = serverpk
        con.crypto_context.clientshorttermpk, \
            con.crypto_context.clientshorttermsk = libnacl.crypto_box_keypair()

        # prepare single valid message
        data = b'123'
        identifier = struct.pack("<8s", b"rZQTd2nM")
        nonce_exp = struct.pack("<16sQ", b"splonebox-server", 4444)
        box = libnacl.crypto_box(
            data, nonce_exp, con.crypto_context.clientshorttermpk, serversk)
        nonce = struct.pack("<Q", 4444)
        length = struct.pack("<Q", 24 + len(box))
        msg = b"".join([identifier, length, nonce, box])

        # this queue simulates the socket receive function and blocks
        # until something is put into the queue
        mc = mock.Mock()
        mock_callback = mock.create_autospec(mc, return_value=b'123')
        socket_recv_q = mocks.connection_socket_fake_recv(con)
        thread = Thread(target=con._listen, args=(mock_callback, ))
        thread.start()

        socket_recv_q.put(msg)
        mock_callback.assert_called_with(b'123')

        # Stop connection thread
        con._connected = False
        thread.join()
