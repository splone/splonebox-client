import socket
import unittest
import unittest.mock as mock
from _thread import start_new_thread

from Splonecli.Rpc.connection import Connection
from Test import mocks


def collect_tests(suite: unittest.TestSuite):
    suite.addTest(ConnectionTest("test_connect"))
    suite.addTest(ConnectionTest("test_send_message"))
    suite.addTest(ConnectionTest("test_listen"))


class ConnectionTest(unittest.TestCase):
    def test_connect(self):
        con = Connection()
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
        con = Connection()

        with self.assertRaises(BrokenPipeError):
            con.send_message(b'123')

    def test_listen(self):
        con = Connection()
        con._connected = True

        mc = mock.Mock()
        mock_callback = mock.create_autospec(mc, return_value=b'123')

        # this queue simulates the socket receive function and blocks
        # until something is put into the queue
        socket_recv_q = mocks.connection_socket_fake_recv(con)

        start_new_thread(con._listen, (mock_callback, ))
        socket_recv_q.put(b'123')
        mock_callback.assert_called_with(b'123')
        con._connected = False

        pass
