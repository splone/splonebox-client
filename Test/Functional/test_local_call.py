import ctypes
import unittest
from _thread import start_new_thread
from queue import Queue
from threading import Lock
from unittest.mock import Mock


from Rpc.message import Message
from Splonecli.Api.apicall import ApiRun
from Splonecli.Api.plugin import Plugin
from Splonecli.Api.remotefunction import RemoteFunction
from Test import mocks


def collect_tests(suite: unittest.TestSuite):
	suite.addTest(LocalCall("test_run_incoming"))
	pass


class LocalCall(unittest.TestCase):
	def test_run_incoming(self):
		mock_foo = Mock()
		sync = Lock()
		sync.acquire()

		def foo(a: ctypes.c_bool, b: ctypes.c_byte, c: ctypes.c_uint64,
				d: ctypes.c_int64, e: ctypes.c_double, f: ctypes.c_char_p,
				g: ctypes.c_long):
			mock_foo(a, b, c, d, e, f, g)
			sync.release()

		RemoteFunction(foo)

		plug = Plugin("abc", "foo", "bar", "bob", "alice", debug=False)
		mocks.plug_rpc_send(plug) # ignore responses here

		# start fake listening
		socket_recv_q = mocks.connection_socket_fake_recv(plug._rpc._connection)
		plug._rpc._connection._connected = True
		start_new_thread(plug._rpc._connection._listen,
						 (plug._rpc._message_callback,))

		# catching responses
		# basically a mock with blocking capability
		call_queue = Queue()

		def fake_send(msg: Message, response_callback=None):
			call_queue.put(msg, timeout=1)

		plug._rpc.send = fake_send

		# pretend that we received a message
		call = ApiRun("id", "foo", [True, b'hi', 5, -82, 7.23, "hi", 64])
		call.msg.arguments[0][0] = None  # remove plugin_id
		call.msg.arguments[0][1] = 123  # set some call id
		socket_recv_q.put(call.msg.pack())

		# give the handling some time
		sync.acquire(timeout=1)
		mock_foo.assert_called_with(True, b'hi', 5, -82, 7.23, "hi", 64)

		# check response
		msg = call_queue.get(timeout=1)
		self.assertEqual(msg.get_type(), 1)
		self.assertEqual(msg.get_msgid(), call.msg.get_msgid())
		self.assertEqual(msg.error, None)
		self.assertEqual(msg.result[0], 123)

		# check result
		msg = call_queue.get(timeout=1)
		self.assertEqual(msg.get_type(), 0)
		self.assertEqual(msg.function, "result")
		self.assertEqual(msg.arguments[0][0], 123)
