import socket
import unittest
import libnacl
import unittest.mock as mock
import struct
from threading import Thread
from multiprocessing import Lock

from splonecli.rpc.connection import Connection
from test import mocks


def collect_tests(suite: unittest.TestSuite):
    suite.addTest(ConnectionTest("test_connect"))
    suite.addTest(ConnectionTest("test_send_message"))
    suite.addTest(ConnectionTest("test_listen"))


class ConnectionTest(unittest.TestCase):
    def test_connect(self):
        con = Connection(libnacl.crypto_box_keypair()[0])

        con._init_crypto = mock.Mock()
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

        execute_lock = Lock()
        execute_lock.acquire()
        mock_callback = mock.Mock()

        def foo(data):
            mock_callback(data)
            execute_lock.release()

        socket_recv_q = mocks.connection_socket_fake_recv(con)
        thread = Thread(target=con._listen, args=(foo, ))
        thread.start()

        socket_recv_q.put(msg)
        execute_lock.acquire()
        mock_callback.assert_called_with(b'123')

        # simulates a message arriving in two pieces
        mock_callback.reset_mock()
        data = bytearray(100)
        nonce_exp = struct.pack("<16sQ", b"splonebox-server", 8888)
        nonce = struct.pack("<Q", 8888)
        box = libnacl.crypto_box(
            data, nonce_exp, con.crypto_context.clientshorttermpk, serversk)
        length = struct.pack("<Q", 24 + len(box))
        msg = b"".join([identifier, length, nonce, box])

        size = 24 + len(box)
        socket_recv_q.put(msg[:int(size/2)])
        socket_recv_q.put(msg[int(size/2):size])
        execute_lock.acquire()
        mock_callback.assert_called_with(data)

        # simulates two messages arriving at the same time
        mock_callback.reset_mock()
        data1 = b"message1"
        nonce_exp = struct.pack("<16sQ", b"splonebox-server", 8890)
        nonce = struct.pack("<Q", 8890)
        box = libnacl.crypto_box(
            data1, nonce_exp, con.crypto_context.clientshorttermpk, serversk)
        length = struct.pack("<Q", 24 + len(box))
        msg1 = b"".join([identifier, length, nonce, box])

        data2 = b"message2"
        nonce_exp = struct.pack("<16sQ", b"splonebox-server", 8892)
        nonce = struct.pack("<Q", 8892)
        box = libnacl.crypto_box(
            data2, nonce_exp, con.crypto_context.clientshorttermpk, serversk)
        length = struct.pack("<Q", 24 + len(box))
        msg2 = b"".join([identifier, length, nonce, box])

        socket_recv_q.put(msg1+msg2)

        execute_lock.acquire()
        mock_callback.assert_called_with(data1)
        mock_callback.reset_mock()

        execute_lock.acquire()
        mock_callback.assert_called_with(data2)
        mock_callback.reset_mock()

        # Stop connection thread
        con._connected = False  # disconnect
        socket_recv_q.put(b'')  # terminate the connection
        thread.join()

        # simulate unexpected termination
        socket_recv_q.put(b'')
        con._connected = True
        with self.assertRaises(BrokenPipeError):
            con._listen(foo)
