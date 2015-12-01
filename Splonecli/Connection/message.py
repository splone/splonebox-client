import msgpack
from msgpack._unpacker import Unpacker

# TODO: This whole thing might get removed. -- Message and Apicall should be merged if possible

class Message:
    """ Mother of all messages. May be a register, request, response or notification message.
        See here for specs: https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md """
    unpacker = Unpacker()

    def __init__(self):
        self._type = None
        self._msgid = 1234  # TODO: super random number
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

    def pack(self) -> bytes:  # Needs to be implemented
        """
        This method is used to serialize the message
        """
        pass

    @staticmethod
    def unpack(s: bytes):
        """
        Unpacks bytes to msgpack-messages

        :param s:  byte stream which ultimately contains a msgpack-formatted message :)
        :return: A List of Message Objects if Messages are available or None
        """
        # TODO: Where should you transform byte in str?
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
                msg.error[1].decode('ascii')
                msg.body = unpacked[3]
                messages.append(msg)

            elif msg._type == 2:
                msg.__class__ = MNotify
                msg.body = unpacked[2]
                messages.append(msg)

            else:
                # TODO: Is this the right way to handle an error? / Is this an error?
                messages.append(None)
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
        return type(self) == type(other) and self._type == other.get_type() and self._msgid == other.get_msgid() \
               and self.method == other.method and self.body == other.body

    def __str__(self):
        return str([self._type, self._msgid, self.method, self.body])

    def pack(self) -> bytes:
        if self._type is None or self._msgid is None or self.body is None or self.method is None:
            return None
        else:
            return msgpack.packb([self._type, self._msgid, self.method, self.body], use_bin_type=True)


class MResponse(Message):
    """
    Response message

    [<message id>, <message type>, <error>, <Message Body>[]]
    """

    def __init__(self):
        super().__init__()
        self.error = None
        self._type = 1

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and self._type == other.get_type() and self._msgid == other.get_msgid() \
               and self.error == other.error and self.body == other.body

    def __str__(self):
        return str([self._type, self._msgid, self.error, self.body])

    def pack(self) -> bytes:
        if self._type is None or self._msgid is None or self.body is None or self.error is None:
            return None
        else:
            return msgpack.packb([self._type, self._msgid, self.error, self.body], use_bin_type=True)


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

    def __str__(self):
        return str([self._type, self._msgid, self.body])

    def pack(self) -> bytes:
        if self._type is None or self._msgid is None or self.body is None:
            return None
        else:
            return msgpack.packb([self._type, self._msgid, self.body], use_bin_type=True)
