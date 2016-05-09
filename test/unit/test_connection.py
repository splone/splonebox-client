from unittest import mock
import unittest
import libnacl
import socket

from test import mocks
from splonebox.rpc.connection import Connection
from splonebox.rpc.crypto import InvalidPacketException, \
    PacketTooShortException


class ConnectionTest(unittest.TestCase):

    def setUp(self):
        self.con = Connection()
        self.con._socket = mock.Mock(spec=socket.socket)

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

    def test_020_send_message(self):
        """ Verify that the box returned by crypto_write is sent. """
        self.con.crypto_context.crypto_established.set()
        self.con._disconnected.clear()

        for data in [b"foobar", libnacl.randombytes(10), b""]:
            self.con.crypto_context.crypto_write = mock.Mock(
                return_value=data)

            self.con.send_message(data)
            self.con._socket.sendall.assert_called_with(data)

        # test send while disconnected
        self.con._disconnected.set()
        with self.assertRaises(BrokenPipeError):
            self.con.send_message(b'foo')

    def test_030_listen_one_packet(self):
        """
        Verify segmentation handling by method '_listen' with one
        packet.

        """
        con = self.con
        con._disconnected.clear()
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

        # put data on to mocked socket(socket will return b'' afterwards)
        buf.append(data)

        con._listen(callback)

        # verify that callback is called
        callback.assert_called_with(data)

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(data)])

        # verify that crypto_read is called with incoming data
        crypto_read.assert_has_calls([mock.call(data)])

    def test_040_listen_two_one_packets(self):
        """ Two crypto messages within one network packet. """
        con = self.con
        con._disconnected.clear()
        buf = mocks.connection_socket_fake_recv(con)

        data = b'data1data2'
        middle = int(len(data) / 2)
        first = data[:middle]  # first packet
        snd = data[middle:]    # second packet

        # the callback function called after decrypting packet
        callback = mock.Mock()

        # mock length
        crypto_verify = mock.Mock()
        crypto_verify.side_effect = [len(first), len(snd)]
        con.crypto_context.crypto_verify_length = crypto_verify

        # mock crypto_read function to return full data in two packets
        crypto_read = mock.Mock()
        crypto_read.side_effect = [first, snd]
        con.crypto_context.crypto_read = crypto_read

        # put data on to mocked socket(socket will return b'' afterwards)
        buf.append(data)

        con._listen(callback)

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(data)])

        # verify that crypto_read is called with incoming data
        crypto_read.assert_has_calls([mock.call(first), mock.call(snd)])

        # verify that callback is called
        callback.assert_has_calls([mock.call(first), mock.call(snd)])

    def test_050_listen_one_two_packets(self):
        """ One crypto message within two network packets. """
        con = self.con
        con._disconnected.clear()
        buf = mocks.connection_socket_fake_recv(con)

        data = libnacl.randombytes(64)
        middle = int(len(data)/2)
        first = data[:middle]  # first packet
        snd = data[middle:]    # second packet

        # the callback function called after decrypting packet
        callback = mock.Mock()

        # mock length
        crypto_verify = mock.Mock()
        crypto_verify.side_effect = [len(data), len(data)]
        con.crypto_context.crypto_verify_length = crypto_verify

        # mock crypto_read function to return full data in two packets
        crypto_read = mock.Mock()
        crypto_read.side_effect = [data]
        con.crypto_context.crypto_read = crypto_read

        # put data on to mocked socket(socket will return b'' afterwards)
        buf.append(first)
        buf.append(snd)

        con._listen(callback)

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(first), mock.call(data)])

        # verify that crypto_read is called with incoming data
        crypto_read.assert_has_calls([mock.call(data)])

        # verify that callback is called
        callback.assert_has_calls([mock.call(data)])

    def test_051_listen_one_two_packets(self):
        """ verify correct handling of PackageTooShortException"""
        con = self.con
        con._disconnected.clear()
        buf = mocks.connection_socket_fake_recv(con)

        data = libnacl.randombytes(64)

        # the callback function called after decrypting packet
        callback = mock.Mock()

        # mock length
        crypto_verify = mock.Mock()
        crypto_verify.side_effect = [PacketTooShortException(), len(data)]
        con.crypto_context.crypto_verify_length = crypto_verify

        # mock crypto_read function to return full data in two packets
        crypto_read = mock.Mock()
        crypto_read.side_effect = [data]
        con.crypto_context.crypto_read = crypto_read

        # put data on to mocked socket (socket will return b'' afterwards)
        buf.append(data[:10])
        buf.append(data[10:])

        con._listen(callback)

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(data[:10]), mock.call(data)])

        # verify that crypto_read is called with incoming data
        crypto_read.assert_has_calls([mock.call(data)])

        # verify that callback is called
        callback.assert_has_calls([mock.call(data)])

    def test_060_listen_failures(self):
        """ Test error handling during listen """
        con = self.con
        con._disconnected.clear()
        callback = mock.Mock()

        con.crypto_context.crypto_verify_length = mock.Mock()

        # test recv returning b''
        mocks.connection_socket_fake_recv(con)
        con._listen(callback)
        self.assertTrue(con._disconnected.is_set())

        con.crypto_context.crypto_verify_length.assert_not_called()

        # test exception raised without prior disconnect
        recv = mock.Mock()
        recv.side_effect = IOError()
        con._socket.recv = recv
        con._disconnected.clear()

        with self.assertRaises(IOError):
            con._listen(callback)

        self.assertTrue(con._disconnected.is_set())

        con.crypto_context.crypto_verify_length.assert_not_called()

        # test exception raised with prior disconnect
        con._socket.recv = mock.Mock()
        con._socket.recv.side_effect = IOError()

        con._disconnected.is_set = mock.Mock()
        con._disconnected.is_set.side_effect = [False, True]

        con._listen(callback)

        con.crypto_context.crypto_verify_length.assert_not_called()

    def test_070_liste_invalid_packet(self):
        """ Test that after receiving an invalid package,
        it get's dropped and the next is handled correctly
        """
        con = self.con
        con._disconnected.clear()
        buf = mocks.connection_socket_fake_recv(con)

        data = bytearray(10)

        # the callback function called after decrypting packet
        callback = mock.Mock()

        # mock length, first throw an exception and then the actual length
        crypto_verify = mock.Mock()
        crypto_verify.side_effect = [InvalidPacketException(), len(data)]
        con.crypto_context.crypto_verify_length = crypto_verify

        # mock crypto_read function to return full data at once
        crypto_read = mock.Mock()
        crypto_read.side_effect = [data]
        con.crypto_context.crypto_read = crypto_read

        # put data on to mocked socket
        # first data is invalid
        # (socket will return b'' afterwards)
        buf.append(libnacl.randombytes(50))
        buf.append(data)

        con._listen(callback)

        # verify that crypto_verify is called with incomming packet
        crypto_verify.assert_has_calls([mock.call(data)])

        # verify that crypto_read is called once with valid data
        crypto_read.assert_called_once_with(data)

        # verify that callback was called only once with valid data
        callback.assert_called_once_with(data)
        # put data on to mocked socket

    def test_080_listen_wrapper(self):
        con = self.con
        callback = mock.Mock()
        con._listen = mock.Mock()

        # test listen without new thread
        con.listen(callback, False)
        con._listen.assert_called_once_with(callback)
        self.assertTrue(con._listen_thread is None)

        con._listen.reset_mock()

        # test listen with new thread
        con.listen(callback, True)
        con._listen.assert_called_once_with(callback)
        self.assertTrue(con._listen_thread is not None)
