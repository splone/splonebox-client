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


from uuid import uuid4
import msgpack


class Message:
    """Mother of all messages. May be a register, request, response
    or notification message. See here for specs:
    https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md
    """

    _max_message_id = pow(2, 32)-1

    def __init__(self):
        self._type = None
        self._msgid = None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def get_type(self) -> int:
        """Returns the type of the message

        :return: Message Type (0: Request, 1: Response, 2: Notify)
        """
        return self._type

    def get_msgid(self) -> int:
        """Returns the message ID

        :return: msg_id
        """
        return self._msgid

    def pack(self) -> bytes:  # Has to be implemented
        """This method is used to serialize the message"""
        pass

    @staticmethod
    def from_unpacked(unpacked):
        """Returns a Request, MResponse or MNotify depending on the type of
        the unpacked message

        :param unpacked: A message unpacked by :msgpack
        :return: :MRequest , :MResponse or MNotify
        :raises :InvalidMessageError if message is not a valid request
        """

        if not isinstance(unpacked, list) or not 2 < len(unpacked) < 5:
            raise InvalidMessageError("Invalid form")

        if not isinstance(unpacked[0], int) or unpacked[0] not in (0, 1, 2):
            raise InvalidMessageError("Invalid type")

        if not isinstance(unpacked[1], int) or unpacked[1] < 0 or unpacked[
                1] > Message._max_message_id:
            raise InvalidMessageError("Invalid Message Id")

        t = unpacked[0]

        if t == 0:
            if not isinstance(unpacked[2], bytes):
                raise InvalidMessageError("Invalid method")
            if not isinstance(unpacked[3], list):
                raise InvalidMessageError("Invalid body")

            msg = MRequest()
            msg._msgid = unpacked[1]
            msg.function = unpacked[2].decode('ascii')
            msg.arguments = unpacked[3]
            return msg

        elif t == 1:
            if unpacked[2] is None and unpacked[3] is None:
                raise InvalidMessageError("error and result are both None")
            if not isinstance(unpacked[2], (list, type(None))):
                raise InvalidMessageError("Invalid Error")
            if not isinstance(unpacked[3], (list, type(None))):
                raise InvalidMessageError("Invalid Result")

            msg = MResponse(unpacked[1])
            msg.error = unpacked[2]
            msg.response = unpacked[3]
            return msg

        elif t == 2:
            if not isinstance(unpacked[2], list):
                raise InvalidMessageError("Notification body is invalid")
            msg = MNotify()
            msg._msgid = unpacked[1]
            msg.body = unpacked[2]
            return msg


class MRequest(Message):
    """Request message
    [<message id>, <message type>, <function name>, <Arguments>[]]
    """

    def __init__(self):
        super().__init__()
        self.function = None
        self.arguments = None
        self._msgid = uuid4().int % Message._max_message_id
        self._type = 0

    def __eq__(self, other) -> bool:
        return self._msgid == other.get_msgid() and \
            self.function == other.function and \
            self.arguments == other.arguments

    def __str__(self) -> str:
        return str([self._type, self._msgid, self.function, self.arguments])

    def pack(self) -> bytes:
        """Packs the request using :msgpack

        :return: message, serialized using msgpack
        :raises :InvalidMessageError if contents are invalid
        """
        if not isinstance(self.function, str) or not isinstance(self.arguments,
                                                                list):
            raise InvalidMessageError("Unable to pack Request message:\n" +
                                      self.__str__())
        else:
            return msgpack.packb(
                [self._type, self._msgid, self.function, self.arguments],
                use_bin_type=True)


class MResponse(Message):
    """Response message
    [<message id>, <message type>, <error>, <response>]
    """

    def __init__(self, msgid: int):
        """
        :param msgid: msgid of the request this message is responding to
        """
        if msgid > Message._max_message_id or msgid < 0:
            raise InvalidMessageError("Invalid Msg id")
        super().__init__()
        self._msgid = msgid
        self.error = None
        self.response = None
        self._type = 1

    def __eq__(self, other) -> bool:
        return self._msgid == other.get_msgid() \
            and self.error == other.error and self.response == other.response

    def __str__(self) -> str:
        return str([self._type, self._msgid, self.error, self.response])

    def pack(self) -> bytes:
        """Packs the response using :msgpack

        :return: message, serialized using msgpack
        """
        if (self.error is None and self.response is None) or\
           not isinstance(self.error, (list, type(None))) or\
           not isinstance(self.response, (list, type(None))):
            raise InvalidMessageError("Unable to pack Response message:\n" +
                                      self.__str__())
        else:
            return msgpack.packb(
                [self._type, self._msgid, self.error, self.response],
                use_bin_type=True)


class MNotify(Message):
    """Notify message
    [<message id>, <message type>, <Message Body>[]]
    """
    def __init__(self):
        super().__init__()
        self.body = None
        self._msgid = uuid4().int % Message._max_message_id
        self._type = 2

    def __eq__(self, other) -> bool:
        return self._msgid == other.get_msgid() and self.body == other.body

    def __str__(self) -> str:
        return str([self._type, self._msgid, self.body])

    def pack(self) -> bytes:
        """Packs the notification using :msgpack

        :return: message, serialized using msgpack
        """
        if not isinstance(self.body, list):
            raise InvalidMessageError("Unable to pack Notification message:\n"
                                      + self.__str__())
        else:
            return msgpack.packb(
                [self._type, self._msgid, self.body],
                use_bin_type=True)


class InvalidMessageError(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self) -> str:
        return self.name
