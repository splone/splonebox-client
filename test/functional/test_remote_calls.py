"""
This file is part of the splonebox python client library.

The splonebox python client library is free software: you can
redistribute it and/or modify it under the terms of the GNU Lesser
General Public License as published by the Free Software Foundation,
either version 3 of the License or any later version.

It is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this splonebox python client library.  If not,
see <http://www.gnu.org/licenses/>.

"""

import ctypes
import socket
import unittest
import msgpack
import libnacl
from unittest.mock import Mock

from splonebox.api.plugin import Plugin
from splonebox.api.remotefunction import RemoteFunction
from test import mocks


class RemoteCallTest(unittest.TestCase):
    def test_register_functional(self):
        def fun2(a: ctypes.c_bool, b: ctypes.c_byte, c: ctypes.c_uint64, d:
                 ctypes.c_int64, e: ctypes.c_double, f: ctypes.c_char_p, g:
                 ctypes.c_long):
            pass

        RemoteFunction(fun2)
        plug = Plugin("abc", "foo", "bar", "bob", "alice")
        mock_send = mocks.rpc_connection_send(plug._rpc)

        plug.register(blocking=False)
        outgoing = msgpack.unpackb(mock_send.call_args[0][0])

        self.assertEqual(0, outgoing[0])
        self.assertEqual(b'register', outgoing[2])
        self.assertEqual(
            [b"abc", b"foo", b"bar", b"bob", b"alice"], outgoing[3][0])
        self.assertIn(
            [b'fun2', b'', [False, b'', 3, -1, 2.0, b'', -1]], outgoing[3][1])

        # cleanup remote_functions
        RemoteFunction.remote_functions = {}

    def test_run_functional(self):
        plug = Plugin("abc", "foo", "bar", "bob", "alice")
        mock_send = mocks.rpc_connection_send(plug._rpc)

        plug.run("plugin_id", "function", [1, "hi", 42.317, b'hi'])
        outgoing = msgpack.unpackb(mock_send.call_args[0][0])

        self.assertEqual(0, outgoing[0])
        self.assertEqual(b'run', outgoing[2])
        self.assertEqual([b'plugin_id', None], outgoing[3][0])
        self.assertEqual(b"function", outgoing[3][1])
        self.assertEqual([1, b'hi', 42.317, b'hi'], outgoing[3][2])

    def test_connect_functional(self):
        plug = Plugin("abc", "foo", "bar", "bob", "alice")

        mock_sock = mocks.connection_socket(plug._rpc._connection)
        plug._rpc._connection.listen = Mock()
        plug._rpc._connection._init_crypto = Mock()

        plug.connect("localhost", 1234)
        ip = mock_sock.connect.call_args[0][0][0]
        port = mock_sock.connect.call_args[0][0][1]

        self.assertEqual(ip, socket.gethostbyname("localhost"))
        self.assertEqual(port, 1234)
