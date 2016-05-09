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
import unittest
import msgpack
from splonebox.api.plugin import Plugin
from splonebox.api.remotefunction import RemoteFunction
from splonebox.rpc.message import MRequest, MResponse
from test import mocks


class CompleteCall(unittest.TestCase):
    def test_complete_run(self):
        # In this test a plugin is created and is calling itself.

        def add(a: ctypes.c_int64, b: ctypes.c_int64):
            "add two ints"
            return a + b

        RemoteFunction(add)

        plug = Plugin("abc", "foo", "bar", "bob", "alice")

        mock_send = mocks.rpc_connection_send(plug._rpc)
        result = plug.run("abc", "add", [7, 8])

        # receive request
        msg = MRequest.from_unpacked(msgpack.unpackb(mock_send.call_args[0][
            0]))
        msg.arguments[0][0] = None  # remove plugin_id
        msg.arguments[0][1] = 123  # set call id
        plug._rpc._message_callback(msg.pack())

        # wait for execution to finish
        plug._active_threads[123].join()

        # receive response
        data = mock_send.call_args_list[1][0][0]
        plug._rpc._message_callback(data)
        self.assertEqual(result._error, None)
        self.assertEqual(result.get_status(), 1)
        self.assertEqual(result.get_id(), 123)

        # receive result request
        # data = mock_send.call_args_list[2][0][0]
        # plug._rpc._message_callback(data)
        # self.assertEqual(result.get_status(), 2)
        # self.assertEqual(result.get_result(blocking=False), [15])

        # cleanup remote_functions
        RemoteFunction.remote_functions = {}

    def test_complete_register(self):
        def fun():
            pass

        RemoteFunction(fun)
        plug = Plugin("abc", "foo", "bar", "bob", "alice")
        mock_send = mocks.rpc_connection_send(plug._rpc)

        result = plug.register(blocking=False)
        outgoing = msgpack.unpackb(mock_send.call_args_list[0][0][0])

        # validate outgoing
        self.assertEqual(0, outgoing[0])
        self.assertEqual(b'register', outgoing[2])
        self.assertEqual(
            [b"abc", b"foo", b"bar", b"bob", b"alice"], outgoing[3][0])
        self.assertIn([b'fun', b'', []], outgoing[3][1])

        # test response handling
        self.assertEqual(result.get_status(), 0)  # no response yet
        response = MResponse(outgoing[1])

        # send invalid response (Second field is set to None)
        plug._rpc._handle_response(response)
        self.assertEqual(result.get_status(), -1)

        # make sure response is only handled once
        with self.assertRaises(KeyError):
            plug._rpc._handle_response(response)

        # test valid response
        result = plug.register(blocking=False)
        outgoing = msgpack.unpackb(mock_send.call_args_list[1][0][0])
        response = MResponse(outgoing[1])
        response.response = []
        plug._rpc._handle_response(response)
        self.assertEqual(result.get_status(), 2)

        # cleanup remote_functions
        RemoteFunction.remote_functions = {}
