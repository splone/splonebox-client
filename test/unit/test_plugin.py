import unittest
from unittest.mock import Mock

import test.mocks as mocks
from splonecli.api.plugin import Plugin
from splonecli.rpc.message import MResponse, MRequest
from splonecli.api.remotefunction import RemoteFunction


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

        self.assertEquals(
            len(call_args.arguments[1]), 0)  # no function registered

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
        send = mocks.plug_rpc_send(plug)  # catch results/responses

        mock = Mock()

        RemoteFunction.remote_functions["foo"] = (mock, ["foo", "", []])

        msg = MRequest()
        msg.function = "run"
        msg.arguments = [[None, 123], b'foo', [1, 1.1, "hi"]]

        plug._handle_run(msg)
        self.assertIsNotNone(plug._active_threads.get(123))

        plug._active_threads.pop(123).join()
        mock.assert_called_with([1, 1.1, "hi"])
        # request was valid -> 1x response + 1x result)
        # self.assertEqual(send.call_count, 2)
        # Change this as soon as result is implemented!
        self.assertEqual(send.call_count, 1)

        send.reset_mock()  # reset call count
        msg.arguments = [[None, 123], b'mock', [1, 1.1, "hi"]]
        plug._handle_run(msg)
        # request was invalid -> 1x error response )
        self.assertEqual(send.call_count, 1)
        with self.assertRaises(KeyError):
            plug._active_threads[123]

        send.reset_mock()  # reset call count
        msg.arguments = [None, b'mock', [1, 1.1, "hi"]]
        plug._handle_run(msg)
        # request was invalid -> 1x error response )
        self.assertEqual(send.call_count, 1)
        with self.assertRaises(KeyError):
            plug._active_threads[123]

        RemoteFunction.remote_functions = {}

    def test_handle_response(self):
        plug = Plugin("abc", "foo", "bar", "bob", "alice")
        send_mock = mocks.plug_rpc_send(plug)

        result = plug.register(blocking=False)
        register_msg = send_mock.call_args[0][0]
        response = MResponse(register_msg._msgid)
        response.response = []
        self.assertEqual(result.get_status(), 0)
        plug._handle_response(response)
        self.assertEqual(result.get_status(), 2)

        result = plug.run("key", "foo", [])
        run_msg = send_mock.call_args[0][0]
        response = MResponse(run_msg._msgid)
        response.response = [123]
        self.assertEqual(result.get_status(), 0)
        plug._handle_response(response)
        self.assertEqual(result.get_status(), 1)
        self.assertEqual(result.get_id(), 123)
