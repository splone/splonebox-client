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


from splonebox.api.apicall import InvalidApiCallError, ApiRun, ApiRegister
from splonebox.rpc.message import MRequest, InvalidMessageError

class ApiCallTest(unittest.TestCase):
    def test_from_msgpack_request(self):
        msg = MRequest()
        msg.function = "run"

        msg.arguments = [[None, 123], b'fun', []]
        call = ApiRun.from_msgpack_request(msg)
        self.assertEqual(call.__class__, ApiRun("a", "b", []).__class__)
        self.assertEqual(call.msg.arguments[1],
                         msg.arguments[1].decode('ascii'))

        msg.function = None
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.function = "run"
        msg.arguments = [[None], b'fun', []]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = [[b'id should not be set', 123], b'fun', []]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = ["not a list", b'fun', []]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = [[None, 123], b'fun', "not a list"]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = [[None, "not an int"], b'fun', []]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = [[None, 123], "not bytes", []]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = 123
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = []
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

        msg.arguments = [[None, 123], b'fun', [None]]
        with self.assertRaises(InvalidMessageError):
            ApiRun.from_msgpack_request(msg)

    def test_apiregister(self):
        metadata = ["plugin_id", "plugin_name", "description", "MIT", "Guy"]
        functions = [["foo", "do_foo", [3, -1, 2.0, "", False, b'']]]
        call = ApiRegister(metadata, functions)

        self.assertEqual(call.msg.function, "register")
        self.assertEqual(call.msg.arguments, [metadata, functions])

        for i in range(5):
            with self.assertRaises(InvalidApiCallError):
                temp = metadata.copy()
                temp[i] = None
                ApiRegister(temp, functions)

        invalid = [0.0, 1, -1, b'hi', True]
        for i in range(5):
            with self.assertRaises(InvalidApiCallError):
                temp = metadata.copy()
                temp[i] = invalid[i]
                ApiRegister(temp, functions)

        with self.assertRaises(InvalidApiCallError):
            ApiRegister(None, functions)

        with self.assertRaises(InvalidApiCallError):
            ApiRegister(metadata, None)

        invalid = [1.2, 800, -92, b'hi', True, "something"]
        for inv in invalid:
            with self.assertRaises(InvalidApiCallError):
                ApiRegister(metadata, [["a", "b", [inv]]])

        with self.assertRaises(InvalidApiCallError):
            ApiRegister(metadata, ["bla"])

        with self.assertRaises(InvalidApiCallError):
            ApiRegister(metadata, [None])

        with self.assertRaises(InvalidApiCallError):
            ApiRegister(metadata, [[1, "do_foo", []]])

        with self.assertRaises(InvalidApiCallError):
            ApiRegister(metadata, [["foo", 1, []]])


    def test_apirun(self):
        plugin_id = "plugin_id"
        function_name = "name"
        args = [0]

        call = ApiRun(plugin_id, function_name, args)
        self.assertEqual(call.msg.function, "run")
        self.assertEqual(call.get_plugin_id(), plugin_id)
        self.assertEqual(call.get_method_name(), function_name)
        self.assertEqual(call.get_method_args(), args)
        self.assertEqual(call.msg.arguments, [[plugin_id, None], function_name,
                                              args])

        with self.assertRaises(InvalidApiCallError):
            ApiRun(2, function_name, args)

        with self.assertRaises(InvalidApiCallError):
            ApiRun(plugin_id, 2, args)

        with self.assertRaises(InvalidApiCallError):
            ApiRun(plugin_id, function_name, [None])

        with self.assertRaises(InvalidApiCallError):
            ApiRun(plugin_id, function_name, [[]])

        with self.assertRaises(InvalidApiCallError):
            ApiRun(plugin_id, function_name, [object()])
