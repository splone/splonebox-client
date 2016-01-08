import unittest
from unittest.mock import Mock

from Splonecli.Rpc.dispatcher import Dispatcher, DispatcherError
from Splonecli.Rpc.message import MRequest, InvalidMessageError


def collect_tests(suite: unittest.TestSuite):
    suite.addTest(DispatcherTest("test_register_function"))
    suite.addTest(DispatcherTest("test_dispatch"))


class DispatcherTest(unittest.TestCase):
    def test_register_function(self):
        fun1 = Mock()

        disp = Dispatcher()

        disp.register_function(fun1, "fun1")
        disp.register_function(fun1, "fun2")

        self.assertIn(fun1, disp._functions.values())
        self.assertIn(fun1, disp._functions.values())
        self.assertEqual(len(disp._functions), 2)

        with self.assertRaises(DispatcherError):
            disp.register_function(fun1, "fun1")

        with self.assertRaises(DispatcherError):
            disp.register_function(fun1, "fun1")

        self.assertEqual(len(disp._functions), 2)

        disp.flush_functions()
        self.assertEqual(len(disp._functions), 0)

    def test_dispatch(self):
        fun1 = Mock()
        fun2 = Mock()
        fun3 = Mock(side_effect=InvalidMessageError("bla"))

        disp = Dispatcher()

        disp.register_function(fun1, "fun1")
        disp.register_function(fun2, "fun2")
        disp.register_function(fun3, "fun3")

        call_fun1 = MRequest()
        call_fun2 = MRequest()
        call_fun3 = MRequest
        call_invalid = MRequest()

        call_fun1.function = "fun1"
        call_fun2.function = "fun2"
        call_fun3.function = "fun3"
        call_invalid.function = "invalid"

        disp.dispatch(call_fun1)
        fun1.assert_called_once_with(call_fun1)

        disp.dispatch(call_fun2)
        fun2.assert_called_once_with(call_fun2)

        with self.assertRaises(DispatcherError):
            disp.dispatch(call_invalid)

        with self.assertRaises(InvalidMessageError):
            disp.dispatch(call_fun3)

        disp.flush_functions()


