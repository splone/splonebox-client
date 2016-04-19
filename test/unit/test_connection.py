from multiprocessing import Lock
from unittest import mock
from threading import Thread
import unittest
import libnacl
import socket
import struct

from splonecli.rpc.connection import Connection
from test import mocks

class ConnectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.con = Connection()
        cls.con._socket = mock.Mock(spec=socket.socket)

    def test_010_connect(self):
        self.con._init_crypto = mock.Mock()

        self.con.connect("127.0.0.1", 6666, None, listen=False)
        self.con._socket.connect.assert_called_with((socket.gethostbyname(
            "127.0.0.1"), 6666))

        some_callback = mock.Mock()
        listen_mock = mocks.Mock()
        self.con.listen = listen_mock

        self.con.connect("127.0.0.1", 6666, some_callback, listen=True)
        listen_mock.assert_called_with(some_callback, new_thread=True)

        self.con._socket.connect.side_effect = ConnectionRefusedError
        with self.assertRaises(ConnectionRefusedError):
            self.con.connect("127.0.0.1", 6666, None, listen=False)

        with self.assertRaises(ConnectionError):
            self.con.connect(1, 1234, None, listen=False)

        with self.assertRaises(ConnectionError):
            self.con.connect("127.0.0.1", "bla", None, listen=False)

    def test_020_send_message(self):
        """ Verify that the box returned by crypto_write is sent. """
        self.con.crypto_context.crypto_established.set()

        for data in [b"foobar", libnacl.randombytes(10), b""]:
            self.con.crypto_context.crypto_write = mock.Mock(
                return_value = data)

            self.con.send_message(data)
            self.con._socket.sendall.assert_called_with(data)

    def test_030_listen_one_packet(self):
        """
        Verify segmentation handling by method '_listing' with one
        packets.

        """
        con = self.con
        con._connected.set()
        buf = mocks.connection_socket_fake_recv(con)

        data = bytearray(10)

        # the callback function called after decrypting packet
        callback = mock.Mock()

        # mock length
        crypto_verify = mock.Mock(return_value=len(data))
        con.crypto_context.crypto_verify_length = crypto_verify

        # mock crypto_read function to return full data at once
        crypto_read = mock.Mock()
        crypto_read.side_effect = [data]
        con.crypto_context.crypto_read = crypto_read

        # put data on to mocked socket
        buf.put(data)

        thread = Thread(target=con._listen, args=(callback, ))
        thread.daemon = True
        thread.start()
        con._connected.clear()

        # verify that callback is called
        callback.assert_called_with(data)

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(data)])

        # verify that crypto_read is called with incoming data
        crypto_read.assert_has_calls([mock.call(data)])


    def test_040_listen_two_packets(self):
        """
        Verify segmentation handling by method 'crypto_read' with two
        packets.

        """
        con = self.con
        con._connected.set()
        buf = mocks.connection_socket_fake_recv(con)

        data = bytearray(20)

        # the callback function called after decrypting packet
        callback = mock.Mock()

        # mock length
        crypto_verify = con.crypto_context.crypto_verify_length

        # mock crypto_read function to return full data in two packets
        crypto_read = con.crypto_context.crypto_read

        middle = int(len(data) / 2)
        first = data[:middle] # first packet
        snd = data[middle:] # second packet
        crypto_read.side_effect = [first, snd]

        # put data on to mocked socket
        buf.put(data)

        thread = Thread(target=con._listen, args=(callback, ))
        thread.daemon = False
        thread.start()
        con._connected.clear()

        buf.put(b'') # should raise an internal exception
        thread.join()

        # verify that callback is called
        callback.assert_has_calls([mock.call(first)])

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(data)])

        # verify that crypto_read is called with incoming data
        crypto_read.assert_has_calls([mock.call(data)])

#        # simulates two messages arriving at the same time
#        mock_callback.reset_mock()
#        data1 = b"message1"
#        nonce_exp = struct.pack("<16sQ", b"splonebox-server", 8890)
#        nonce = struct.pack("<Q", 8890)
#        box = libnacl.crypto_box(data1, nonce_exp,
#            self.con.crypto_context.clientshorttermpk, serversk)
#        length = struct.pack("<Q", 24 + len(box))
#        msg1 = b"".join([identifier, length, nonce, box])
#
#        data2 = b"message2"
#        nonce_exp = struct.pack("<16sQ", b"splonebox-server", 8892)
#        nonce = struct.pack("<Q", 8892)
#        box = libnacl.crypto_box(data2, nonce_exp,
#            self.con.crypto_context.clientshorttermpk, serversk)
#        length = struct.pack("<Q", 24 + len(box))
#        msg2 = b"".join([identifier, length, nonce, box])
#
#        socket_recv_q.put(msg1+msg2)
#
#        execute_lock.acquire()
#        mock_callback.assert_called_with(data1)
#        mock_callback.reset_mock()
#
#        execute_lock.acquire()
#        mock_callback.assert_called_with(data2)
#        mock_callback.reset_mock()

