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

from splonebox.rpc.message import MRequest, Message, MResponse, MNotify, \
 InvalidMessageError

class MessageTest(unittest.TestCase):
    def test_unpack(self):
        msg_request = [0, 1, b'run', [b'hi']]
        unpacked = Message.from_unpacked(msg_request)
        self.assertEqual(unpacked._type, 0)
        self.assertEqual(unpacked.get_msgid(), 1)
        self.assertEqual(unpacked.arguments, [b'hi'])
        self.assertEqual(unpacked.function, "run")

        msg_response = [1, 1, ['err'], ['res']]
        unpacked = Message.from_unpacked(msg_response)
        self.assertEqual(unpacked._type, 1)
        self.assertEqual(unpacked.get_msgid(), 1)
        self.assertEqual(unpacked.error, ['err'])
        self.assertEqual(unpacked.response, ['res'])

        msg_notify = [2, 1, ['hi']]
        unpacked = Message.from_unpacked(msg_notify)
        self.assertEqual(unpacked._type, 2)
        self.assertEqual(unpacked.get_msgid(), 1)
        self.assertEqual(unpacked.body, ['hi'])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, 2])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, 2, 3, 4, 5])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked(["", 1, ['err'], ['res']])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([5, 1, ['err'], ['res']])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, "", ['err'], ['res']])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, -1, ['err'], ['res']])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, pow(2, 32) + 1, ['err'], ['res']])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([0, 1, "", [""]])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([0, 1, b'', ""])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, 1, None, None])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, 1, "", []])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, 1, [], ""])

        with self.assertRaises(InvalidMessageError):
            Message.from_unpacked([1, 1, ""])

    def test_MRequest(self):
        msg = MRequest()
        msg.function = "foo"
        msg.arguments = []
        self.assertEqual(msg.pack(), msgpack.packb([0, msg._msgid, "foo", []]))

        with self.assertRaises(InvalidMessageError):
            msg.arguments = None
            msg.pack()

        with self.assertRaises(InvalidMessageError):
            msg.function = None
            msg.arguments = []
            msg.pack()
        pass

    def test_MResponse(self):
        with self.assertRaises(InvalidMessageError):
            MResponse(-1)

        with self.assertRaises(InvalidMessageError):
            MResponse(pow(2, 32) + 1)

        msg = MResponse(1)
        msg.error = []
        msg.response = []
        self.assertEqual(msg.pack(), msgpack.packb([1, 1, [], []]))

        with self.assertRaises(InvalidMessageError):
            msg.error = ""
            msg.pack()

        with self.assertRaises(InvalidMessageError):
            msg.response = ""
            msg.error = []
            msg.pack()

        with self.assertRaises(InvalidMessageError):
            msg.response = None
            msg.error = None
            msg.pack()

    def test_MNotify(self):
        msg = MNotify()
        msg.body = []
        self.assertEqual(msg.pack(), msgpack.packb([2, msg._msgid, []]))

        with self.assertRaises(InvalidMessageError):
            msg.body = ""
            msg.pack()
