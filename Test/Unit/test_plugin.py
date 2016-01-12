import unittest
from unittest.mock import Mock
import Test.mocks as mocks
from Splonecli.Api.plugin import Plugin
from Splonecli.Rpc.message import MResponse, MRequest
from Splonecli.Api.remotefunction import RemoteFunction


def collect_tests(suite: unittest.TestSuite):
	suite.addTest(PluginTest('test_register'))
	suite.addTest(PluginTest('test_connect'))
	suite.addTest(PluginTest('test_run'))
	suite.addTest(PluginTest('test_handle_response'))
	suite.addTest(PluginTest('test_handle_run'))


class PluginTest(unittest.TestCase):
	def test_register(self):
		plug = Plugin("abc", "foo", "bar", "bob", "alice", debug=False)

		rpc_send_mock = mocks.plug_rpc_send(plug)
		plug.register(blocking=False)
		call_args = rpc_send_mock.call_args[0][0]

		self.assertEqual(call_args._type, 0)  # 0 indicates message request

		self.assertTrue(0 <= call_args._msgid < pow(2, 32))  # valid msgid

		self.assertEqual(call_args.function, 'register')  # register request

		self.assertEqual(call_args.arguments[0],
						 ['abc', 'foo', 'bar', 'bob', 'alice'])  # metadata

		self.assertEqual(call_args.arguments[1][0],
						 RemoteFunction.remote_functions['stop'][
							 1])  # default stop function

		self.assertEquals(len(call_args.arguments[1]),
						  1)  # no other functions registered

	def test_connect(self):
		plug = Plugin("abc", "foo", "bar", "bob", "alice")
		connect_rpc_mock = mocks.plug_rpc_connect(plug)

		plug.connect("hostname", 1234)
		connect_rpc_mock.assert_called_with("hostname", 1234)

	# Note: connect is just a wrapper for Connection.connect()

	def test_run(self):
		plug = Plugin("abc", "foo", "bar", "bob", "alice")

		rpc_send_mock = mocks.plug_rpc_send(plug)

		plug.run("apikey", "foo", [1, "foo"])
		call_args = rpc_send_mock.call_args[0][0]

		self.assertEqual(call_args._type, 0)  # 0 indicates message request
		self.assertTrue(0 <= call_args._msgid < pow(2, 32))  # valid msgid
		self.assertEqual(call_args.function, 'run')  # run request
		self.assertEqual(call_args.arguments[0][0], "apikey")
		self.assertEqual(call_args.arguments[1], "foo")
		self.assertEqual(call_args.arguments[2], [1, "foo"])
		pass

	def test_handle_run(self):
		plug = Plugin("abc", "foo", "bar", "bob", "alice")
		mocks.plug_rpc_send(plug)

		mock = Mock()
		RemoteFunction.remote_functions["mock"] = (mock, ["mock", "", []])

		msg = MRequest()
		msg.function = "run"
		msg.arguments = [[b'apikey'], b'mock', [1, 1.1, "hi"]]

		plug._handle_run(msg)
		mock.assert_called_with([1, 1.1, "hi"])

		msg.arguments = [[b'apikey'], b'foo', [1, 1.1, "hi"]]
		plug._handle_run(msg)

		msg.arguments = [None, b'mock', [1, 1.1, "hi"]]
		plug._handle_run(msg)

		RemoteFunction.remote_functions = {}

	def test_handle_response(self):
		plug = Plugin("abc", "foo", "bar", "bob", "alice")
		send_mock = mocks.plug_rpc_send(plug)

		result = plug.register(blocking=False)
		register_msg = send_mock.call_args[0][0]
		response = MResponse(register_msg._msgid)
		response.result = []
		self.assertEqual(result.get_status(), 0)
		plug._handle_response(response)
		self.assertEqual(result.get_status(), 2)

		result = plug.run("key", "foo", [])
		run_msg = send_mock.call_args[0][0]
		response = MResponse(run_msg._msgid)
		response.result = [123]
		self.assertEqual(result.get_status(), 0)
		plug._handle_response(response)
		self.assertEqual(result.get_status(), 1)
		self.assertEqual(result.get_id(), 123)

		result_request = MRequest()
		result_request.function = "result"
		result_request.arguments =[[123], ["Some Result!"]]
		plug._handle_result(result_request)

		self.assertEqual(result.get_result()[0], 2)
		self.assertEqual(result.get_result()[1], ["Some Result!"])

