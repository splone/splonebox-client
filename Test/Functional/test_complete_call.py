import ctypes
import unittest

import msgpack

from Splonecli.Api.plugin import Plugin
from Splonecli.Api.remotefunction import RemoteFunction
from Rpc.message import MRequest
from Test import mocks


def collect_tests(suite: unittest.TestSuite):
	suite.addTest(CompleteCall("test_complete_run"))
	pass


class CompleteCall(unittest.TestCase):
	def test_complete_run(self):
		# In this test a plugin is created and is calling itself.

		def add(a: ctypes.c_int64, b: ctypes.c_int64):
			"add two ints"
			return a + b
		RemoteFunction(add)

		plug = Plugin("abc", "foo", "bar", "bob", "alice")

		mock_sock = mocks.connection_socket(plug._rpc._connection)
		result = plug.run("abc", "add", [7, 8])

		# receive request
		msg = MRequest.from_unpacked(msgpack.unpackb(mock_sock.send.call_args[0][0]))
		msg.arguments[0][0] = None  # remove plugin_id
		msg.arguments[0][1] = 123  # set call id
		plug._rpc._message_callback(msg.pack())

		# receive response
		data = mock_sock.send.call_args_list[1][0][0]
		plug._rpc._message_callback(data)
		self.assertEqual(result._error, None)
		self.assertEqual(result.get_status(), 1)
		self.assertEqual(result.get_id(), 123)

		# receive result request
		data = mock_sock.send.call_args_list[2][0][0]
		plug._rpc._message_callback(data)
		self.assertEqual(result.get_status(), 2)
		self.assertEqual(result.get_result(blocking=False), [15])

