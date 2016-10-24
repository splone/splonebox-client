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

import copy

from splonebox.rpc.message import MRequest, MNotify, InvalidMessageError


class ApiCall:
    """Wraps :class:`Message` for convenience and type checks

    Splonebox specific messages are defined here
    """

    def __init__(self):
        self.msg = MRequest()


class ApiRegister(ApiCall):
    """Register api call.

        :param metadata: The Plugins Metadata
                    ["name", "description", "author", "license"]

        :param functions: list of function descriptions
                    [[name,desc,[arg1,arg2..]], ...]

        :raises InvalidApiCallError: if the information is invalid
    """
    _valid_args = ["", 3, -1, False, 2.0, b'']

    def __init__(self, metadata: [], functions: []):
        super().__init__()
        if metadata is None or None in metadata:
            raise InvalidApiCallError("Plugin's metadata is not set properly")

        for meta in metadata:
            if not isinstance(meta, str):
                raise InvalidApiCallError("Metadata's type has to be string!")

        if functions is None or not isinstance(functions, type([[]])):
            raise InvalidApiCallError("Malformed functions parameter")

        for fun_meta in functions:
            if fun_meta is None:
                raise InvalidApiCallError("function can not be None")
            if not isinstance(fun_meta[0], str):
                raise InvalidApiCallError("Function name has to be string!")
            if not isinstance(fun_meta[1], str):
                raise InvalidApiCallError(
                    "Function description has to be string!")
            for arg in fun_meta[2]:
                # (1 == True) is True..
                if (arg, type(arg)) not in map(lambda x: (x, type(x)),
                                               ApiRegister._valid_args):
                    raise InvalidApiCallError(
                        "Invalid Type identifier in  argument list")

        self.msg.function = "register"
        self.msg.arguments = [metadata, functions]


class ApiRun(ApiCall):
    """Run api call
    :param plugin_id: plugin identifier of the plugin to be called
    :param function_name: function wto be called
    :param args: list of arguments for the remote function
    :raises InvalidApiCallError: if the Information is invalid
    """
    _valid_types = (str, bytes, int, float, bool)

    def __init__(self, plugin_id: str, function_name: str, args: []):
        super().__init__()

        if not isinstance(plugin_id, str):
            raise InvalidApiCallError("plugin identifier has to be a string")

        if not isinstance(function_name, str):
            raise InvalidApiCallError("function name has to be a string")

        if args is None:
            args = []

        for arg in args:
            if not isinstance(arg, ApiRun._valid_types):
                raise InvalidApiCallError("Invalid Argument type!")

        self.msg = MRequest()
        self.msg.function = "run"
        self.msg.arguments = [[plugin_id, None], function_name, args]

    @staticmethod
    def from_msgpack_request(msg: MRequest):
        """ Generates an ApiRun object from a given MRequest

        :param msg: A Request received and unpacked with MsgpackRpc. It is
                    assumed, that the strings in msg.body are still in
                    binary format!
        :return: ApiRun
        :raises  InvalidMessageError: if provided message is
                    not a valid Run call
        """

        if not isinstance(msg.function, str) or msg.function != "run":
            raise InvalidMessageError(
                "Invalid run Request, specified method is not run")

        if not isinstance(msg.arguments, list) or len(msg.arguments) != 3:
            raise InvalidMessageError("Message body is faulty")

        if not isinstance(msg.arguments[0],
                          list) or len(msg.arguments[0]) != 2:
            raise InvalidMessageError("First element of body has to be a list")

        if msg.arguments[0][0] is not None:
            raise InvalidMessageError("Plugin identifier set on incomming msg")

        if not isinstance(msg.arguments[0][1], int):
            raise InvalidMessageError("Call_id is invaild")

        if not isinstance(msg.arguments[1], bytes):
            raise InvalidMessageError("Function name is not bytes")

        if not isinstance(msg.arguments[2], list):
            raise InvalidMessageError("Third element of body has to be a list")

        msg = copy.deepcopy(msg)
        msg.arguments[1] = msg.arguments[1].decode('ascii')

        for arg in msg.arguments[2]:
            if not isinstance(arg, ApiRun._valid_types):
                raise InvalidMessageError("Invalid Argument type!")

        call = ApiRun("", msg.arguments[1], msg.arguments[2])
        call.msg._msgid = msg._msgid  # keep the original msg_id

        return call

    def get_method_args(self):
        return self.msg.arguments[2]

    def get_plugin_id(self) -> str:
        return self.msg.arguments[0][0]

    def get_method_name(self) -> str:
        return self.msg.arguments[1]


class ApiResult(ApiCall):
    """Result api call

    :param call_id: The result is related to this call id
    :param result: The call's result (is automatically wrapped in a list)
    """
    def __init__(self, call_id: int, result):
        super().__init__()

        if not isinstance(call_id, int):
            raise InvalidApiCallError("call_id has to be an integer")

        if result is None:
            raise InvalidApiCallError("Result can not be none!")

        self.msg.function = "result"
        self.msg.arguments = [[call_id], [result]]

    @staticmethod
    def from_msgpack_request(msg: MRequest):

        if not isinstance(msg.function, str) or msg.function != "result":
            raise InvalidMessageError(
                "Invalid result Request, specified method is not result")

        if not isinstance(msg.arguments, list):
            raise InvalidMessageError(
                "Invalid result Request, arguments is not a list")

        if len(msg.arguments) != 2:
            raise InvalidMessageError(
                "Invalid result Request, arguments length has to be 2")

        if not isinstance(msg.arguments[0], list) or len(msg.arguments[0]) != 1:
            raise InvalidMessageError(
                "Invalid result Request, call_id is not in a list")

        if not isinstance(msg.arguments[1], list) or len(msg.arguments[1]) != 1:
            raise InvalidMessageError(
                "Invalid result Request, result is not in a list")

        result = ApiResult(msg.arguments[0][0], msg.arguments[1][0])
        result.msg._msgid = msg._msgid

        return result

    def get_call_id(self) -> int:
        return self.msg.arguments[0][0]

    def get_result(self):
        return self.msg.arguments[1][0]


class ApiBroadcast(ApiCall):
    def __init__(self, event_name: str, args: [], as_notification=True):
        super().init()

        if not isinstance(event_name, str):
            raise InvalidApiCallError("Event name has to be string")

        # This is for simple "ping" notifications
        if args is None:
            args = []

        if not isinstance(args, list):
            raise InvalidApiCallError("Event args have to be list or None")

        if as_notification:
            self.msg = MNotify("broadcast", [event_name, args])
        else:
            self.msg.function = "broadcast"
            self.msg.arguments = [event_name, args]


class ApiSubscribe(ApiCall):
    def __init__(self, event_name: str):
        if not isinstance(event_name, str):
            raise InvalidApiCallError("Event name has to be string")

        self.msg.function = "subscribe"
        self.msg.arguments = [event_name]


class ApiUnsubscribe(ApiCall):
    def __init__(self, event_name: str):
        if not isinstance(event_name, str):
            raise InvalidApiCallError("Event name has to be string")
        self.msg.function = "unsubscribe"
        self.msg.arguments = [event_name]


class InvalidApiCallError(Exception):
    pass
