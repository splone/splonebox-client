import unittest
from unittest.mock import Mock
from Splonecli.Rpc.message import MRequest, InvalidMessageError, MNotify, \
	MResponse
from Splonecli.Rpc.msgpackrpc import MsgpackRpc
from Test import mocks


def collect_tests(suite: unittest.TestSuite):
	suite.addTest(MsgpackRpcTest("test_send"))
	suite.addTest(MsgpackRpcTest("test_message_callback"))
	suite.addTest(MsgpackRpcTest("test_handle_response"))
	pass


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

		rpc._message_callback(m_res.pack())
		self.assertEqual(mock_send.call_args[0][0].error[1],
						 "Could not handle request! res")

		rpc._message_callback(m_req.pack())
		self.assertEqual(mock_send.call_args[0][0].error[1],
						 "Could not handle request! req")

	def test_handle_response(self):
		rpc = MsgpackRpc()
		response = MResponse(1234)
		response.response = []
		mock_callback = Mock()

		rpc._response_callbacks[1234] = mock_callback

		rpc._handle_response(response)
		mock_callback.assert_called_with(response)

		with self.assertRaises(KeyError):
			rpc._handle_response(response)
