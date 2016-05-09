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
from unittest.mock import Mock

from splonebox.api.apicall import ApiRun
from splonebox.api.plugin import Plugin
from splonebox.api.remotefunction import RemoteFunction
from test import mocks


class LocalCall(unittest.TestCase):
    def test_run_incoming(self):
        mock_foo = Mock()

        def foo(a: ctypes.c_bool, b: ctypes.c_byte, c: ctypes.c_uint64, d:
                ctypes.c_int64, e: ctypes.c_double, f: ctypes.c_char_p, g:
                ctypes.c_long):
            mock_foo(a, b, c, d, e, f, g)

        RemoteFunction(foo)

        plug = Plugin("abc", "foo", "bar", "bob", "alice")
        mocks.plug_rpc_send(plug)  # ignore responses here

        mock_send = mocks.rpc_send(plug._rpc)

        # pretend that we received a message
        call = ApiRun("id", "foo", [True, b'hi', 5, -82, 7.23, "hi", 64])
        call.msg.arguments[0][0] = None  # remove plugin_id
        call.msg.arguments[0][1] = 123  # set some call id
        plug._rpc._message_callback(call.msg.pack())

        # wait for execution to finish
        plug._active_threads[123].join()
        mock_foo.assert_called_with(True, b'hi', 5, -82, 7.23, "hi", 64)

        # check response
        msg = mock_send.call_args_list[0][0][0]
        self.assertEqual(msg.get_type(), 1)
        self.assertEqual(msg.get_msgid(), call.msg.get_msgid())
        self.assertEqual(msg.error, None)
        self.assertEqual(msg.response[0], 123)

        # check result
        # msg = mock_send.call_args_list[1][0][0]
        # self.assertEqual(msg.get_type(), 0)
        # self.assertEqual(msg.function, "result")
        # self.assertEqual(msg.arguments[0][0], 123)

        # cleanup remote_functions
        RemoteFunction.remote_functions = {}
