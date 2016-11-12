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

import unittest
from unittest.mock import Mock

import test.mocks as mocks
from splonebox.api.plugin import Plugin
from splonebox.api.core import Core
from splonebox.api.remotefunction import RemoteFunction
from splonebox.rpc.message import MRequest


class PluginTest(unittest.TestCase):
    def setUp(self):
        # cleanup remote_functions
        RemoteFunction.remote_functions = []

    def test_00_register(self):
        core = Core()
        plug = Plugin("foo", "bar", "bob", "alice", core)

        rpc_send_mock = mocks.core_rpc_send(core)

        plug.register(blocking=False)
        call_args = rpc_send_mock.call_args[0][0]

        self.assertEqual(call_args._type, 0)  # 0 indicates message request

        self.assertTrue(0 <= call_args._msgid < pow(2, 32))  # valid msgid

        self.assertEqual(call_args.function, 'register')  # register request

        self.assertEqual(call_args.arguments[0],
                         ['foo', 'bar', 'bob', 'alice'])  # metadata

        self.assertEquals(
            len(call_args.arguments[1]), 0)  # no function registered

    def test_10_handle_run(self):
        core = Core()
        plug = Plugin("foo", "bar", "bob", "alice", core)
        send = mocks.core_rpc_send(core)  # catch results/responses

        mock = Mock()
        mock.__name__ = "foo"
        mock.return_value = "return"
        plug.functions["foo"] = mock
        plug.function_meta["foo"] = (["", []])

        msg = MRequest()
        msg.function = "run"
        msg.arguments = [[None, 123], b'foo', [1, 1.1, "hi"]]

        error, response = plug._handle_run(msg)
        self.assertIsNotNone(plug._active_threads.get(123))

        plug._active_threads.pop(123).join()
        mock.assert_called_with([1, 1.1, "hi"])
        # request was valid  + 1x result
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args_list[0][0][0].arguments[0][0], 123)
        self.assertEqual(send.call_args_list[0][0][0].arguments[1][0],
                         "return")

        # (response is sent by msgpack-rpc handler)
        self.assertEqual(response, [123])
        self.assertIsNone(error)

        send.reset_mock()  # reset call count
        msg.arguments = [[None, 123], b'mock', [1, 1.1, "hi"]]
        error, response = plug._handle_run(msg)
        # request was invalid -> error response
        self.assertEqual(error, [404, "Function does not exist!"])
        self.assertIsNone(response)
        with self.assertRaises(KeyError):
            plug._active_threads[123]

        send.reset_mock()  # reset call count
        msg.arguments = [None, b'mock', [1, 1.1, "hi"]]
        error, response = plug._handle_run(msg)
        # request was invalid -> error response
        self.assertEqual(error, [400, "Message is not a valid run call"])
        self.assertIsNone(response)

        with self.assertRaises(KeyError):
            plug._active_threads[123]
