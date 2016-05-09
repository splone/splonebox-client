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
import msgpack
from unittest.mock import Mock
from splonebox.rpc.message import MRequest, InvalidMessageError, MNotify, \
 MResponse
from splonebox.rpc.msgpackrpc import MsgpackRpc
from test import mocks


class MsgpackRpcTest(unittest.TestCase):
    def test_send(self):
        rpc = MsgpackRpc()
        con_send_mock = mocks.rpc_connection_send(rpc)
        m1 = MRequest()

        with self.assertRaises(InvalidMessageError):
            rpc.send(m1)

        m1.function = "run"
        m1.arguments = []

        rpc.send(m1)
        self.assertIsNone(rpc._response_callbacks.get(m1.get_msgid()))

        con_send_mock.assert_called_once_with(m1.pack())
        con_send_mock.reset_mock()

        def r_cb():
            pass

        rpc.send(m1, r_cb)
        self.assertEqual(rpc._response_callbacks[m1.get_msgid()], r_cb)

        con_send_mock.side_effect = BrokenPipeError()
        with self.assertRaises(BrokenPipeError):
            rpc.send(m1)

        with self.assertRaises(InvalidMessageError):
            rpc.send(None)

    # noinspection PyProtectedMember
    def test_message_callback(self):
        rpc = MsgpackRpc()

        dispatch = mocks.rpc_dispatch(rpc, "run")
        m_req = MRequest()
        m_req.function = "run"
        m_req.arguments = []

        rpc._message_callback(m_req.pack())
        dispatch.assert_called_once_with(m_req)

        handle_response = mocks.rpc_handle_response(rpc)
        m_res = MResponse(1)
        m_res.response = []
        rpc._message_callback(m_res.pack())
        handle_response.assert_called_once_with(m_res)

        handle_notify = mocks.rpc_handle_notify(rpc)
        m_not = MNotify()
        m_not.body = []
        rpc._message_callback(m_not.pack())
        handle_notify.assert_called_once_with(m_not)

        handle_notify.side_effect = InvalidMessageError("not")
        handle_response.side_effect = InvalidMessageError("res")
        dispatch.side_effect = InvalidMessageError("req")

        mock_send = mocks.rpc_send(rpc)

        rpc._message_callback(m_not.pack())
        self.assertEqual(mock_send.call_args[0][0].error[1],
                         "Could not handle request! not")

        handle_notify.side_effect = TypeError()
        rpc._message_callback(m_not.pack())
        self.assertEqual(mock_send.call_args[0][0].error[1],
                         "Unexpected exception occurred!")

        rpc._message_callback(m_res.pack())
        self.assertEqual(mock_send.call_args[0][0].error[1],
                         "Could not handle request! res")

        rpc._message_callback(m_req.pack())
        self.assertEqual(mock_send.call_args[0][0].error[1],
                         "Could not handle request! req")

        rpc._message_callback(msgpack.packb(["hi"]))
        self.assertEqual(mock_send.call_args[0][0].error[1],
                         "Invalid Message Format")

        # handle unexpected exception
        handle_notify.side_effect = TypeError()
        rpc._message_callback(m_not.pack())
        self.assertEqual(mock_send.call_args[0][0].error[1],
                         "Unexpected exception occurred!")

    def test_handle_response(self):
        rpc = MsgpackRpc()
        response = MResponse(1234)
        response.response = []
        mock_callback = Mock()

        rpc._response_callbacks[1234] = mock_callback
        rpc._response_callbacks[1234] = mock_callback

        rpc._handle_response(response)
        mock_callback.assert_called_with(response)

        # unrelated response
        with self.assertRaises(KeyError):
            rpc._handle_response(response)

        # unrelated error response
        response.response = None
        response.error = [404, "Unrelated"]
        with self.assertRaises(KeyError):
            rpc._handle_response(response)
