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

from splonebox.api.remotefunction import RemoteFunction


@RemoteFunction
def fun1():
    pass


@RemoteFunction
def fun2(a: ctypes.c_bool, b: ctypes.c_byte, c: ctypes.c_uint64, d:
         ctypes.c_int64, e: ctypes.c_double, f: ctypes.c_char_p, g:
         ctypes.c_long):
    pass


@RemoteFunction
def fun3():
    """Some Docstring"""
    pass


@RemoteFunction
def fun4(a, b):
    pass


@RemoteFunction
def fun5(a: ctypes.c_bool, b, c):
    pass


class RemoteFunctionTest(unittest.TestCase):
    def test_annotation(self):
        functions = RemoteFunction.remote_functions

        self.assertTrue("fun1" in functions.keys())
        f = functions["fun1"]
        self.assertEqual(f[0], fun1)
        self.assertEqual(f[1][0], "fun1")
        self.assertEqual(f[1][1], "")
        self.assertEqual(f[1][2], [])

        self.assertTrue("fun2" in functions.keys())
        f = functions["fun2"]
        self.assertEqual(f[0], fun2)
        self.assertEqual(f[1][0], "fun2")
        self.assertEqual(f[1][1], "")
        self.assertEqual(f[1][2], [False, b'', 3, -1, 2.0, "", -1])

        self.assertTrue("fun3" in functions.keys())
        f = functions["fun3"]
        self.assertEqual(f[0], fun3)
        self.assertEqual(f[1][0], "fun3")
        self.assertEqual(f[1][1], "Some Docstring")
        self.assertEqual(f[1][2], [])

        self.assertTrue("fun4" not in functions.keys())
        self.assertTrue("fun5" not in functions.keys())

        RemoteFunction.remote_functions = {}

    def test_call(self):
        fun2.fun = Mock()
        fun2([True, b'', 0, -1, 0.0, b'', -1])
        fun2.fun.assert_called_with(True, b'', 0, -1, 0.0, "", -1)

        with self.assertRaises(TypeError):
            fun2([0])

        RemoteFunction.remote_functions = {}
