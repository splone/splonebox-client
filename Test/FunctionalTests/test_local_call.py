import ctypes
import unittest
import unittest.mock as mock
from _thread import start_new_thread
from unittest.mock import Mock

from multiprocessing import Lock

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

		# start fake listening
		socket_recv_q = mocks.connection_socket_fake_recv(plug._rpc._connection)
		plug._rpc._connection._connected = True
		start_new_thread(plug._rpc._connection._listen,
						 (plug._rpc._message_callback,))

		# pretend that we received a message
		socket_recv_q.put(ApiRun("apikey", "foo",
								 [True, b'hi', 5, -82, 7.23, "hi",
								  64]).msg.pack())
		# give the handling some time
		sync.acquire(timeout=1)
		mock_foo.assert_called_with(True, b'hi', 5, -82, 7.23, "hi", 64)
		plug._rpc._connection._connected = False
