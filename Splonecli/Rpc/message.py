from uuid import uuid4

import msgpack


class Message:
    """ Mother of all messages. May be a register, request, response or notification message.
        See here for specs: https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md """
    unpacker = msgpack.Unpacker()

    def __init__(self):
        self._type = None
        self._msgid = uuid4().int >> 96
        # TODO: There might me more to this
        self.body = None

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def get_type(self) -> int:
        """
        Returns the type of the message

        :return: Message Type (0: Request, 1: Response, 2: Notify)
        """
        return self._type

    def get_msgid(self) -> int:
        """
        Returns the message ID
        :return: Some random Message ID
        """
        return self._msgid

    def pack(self) -> bytes:  # Has to be implemented
        """
        This method is used to serialize the message
        """
        pass

    @staticmethod
    def unpack(s: bytes) -> []:
        """
        deserializes bytes to msgpack-messages

        :param s:  byte stream which ultimately contains a msgpack-formatted message :)
        :return: A List of Message Objects if Messages are available or None
        """
        Message.unpacker.feed(s)
        messages = []
        for unpacked in Message.unpacker:
            msg = Message()
            msg._type = unpacked[0]
            msg._msgid = unpacked[1]

            if msg._type == 0:
                msg.__class__ = MRequest
                msg.method = unpacked[2].decode('ascii')
                msg.body = unpacked[3]
                messages.append(msg)

            elif msg._type == 1:
                msg.__class__ = MResponse
                msg.error = unpacked[2]
                msg.body = unpacked[3]
                messages.append(msg)

            elif msg._type == 2:
                msg.__class__ = MNotify
                msg.body = unpacked[2]
                messages.append(msg)

            else:
                msg._type = -1  # INVALID MESSAGE!

        return messages


class MRequest(Message):
    """
    Request message

    [<message id>, <message type>, <method name>, <Arguments>[]]
    """

    def __init__(self):
        super().__init__()
        self.method = None
        self._type = 0

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and self._type == other.get_type() \
               and self._msgid == other.get_msgid() \
               and self.method == other.method and self.body == other.body

    def __str__(self) -> str:
        return str([self._type, self._msgid, self.method, self.body])

    def pack(self) -> bytes:
        if self._type is None or self._msgid is None or self.body is None \
                or self.method is None:
            raise InvalidMessageError("Unable to pack Request message:\n" + self.__str__())
        else:
            return msgpack.packb([self._type, self._msgid, self.method, self.body],
                                 use_bin_type=True)


class MResponse(Message):
    """
    Response message

    [<message id>, <message type>, <error>, <result>]
    """

    def __init__(self, msgid: int):
        super().__init__()
        self._msgid = msgid
        self.error = None
        self._type = 1

    def __eq__(self, other) -> bool:
        return type(self) == type(
            other) and self._type == other.get_type() and self._msgid == other.get_msgid() \
               and self.error == other.error and self.body == other.body

    def __str__(self) -> str:
        return str([self._type, self._msgid, self.error, self.body])

    def pack(self) -> bytes:
        if self._type is None or self._msgid is None or (self.error is None and self.body is None):
            raise InvalidMessageError("Unable to pack Response message:\n" + self.__str__())
        else:
            return msgpack.packb([self._type, self._msgid, self.error, self.body],
                                 use_bin_type=True)


class MNotify(Message):
    """
    Response message

    [<message id>, <message type>, <Message Body>[]]
    """

    def __init__(self):
        super().__init__()
        self._type = 2

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and self._type == other.get_type() \
               and self._msgid == other.get_msgid() and self.body == other.body

    def __str__(self) -> str:
        return str([self._type, self._msgid, self.body])

    def pack(self) -> bytes:
        if self._type is None or self._msgid is None or self.body is None:
            raise InvalidMessageError("Unable to pack Notification message:\n" + self.__str__())
        else:
            return msgpack.packb(
                [self._type, self._msgid, self.body], use_bin_type=True)


class InvalidMessageError(Exception):
    # TODO: Maybe add a separate exception for handling more specific errors
    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return self.value
