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
from types import FunctionType


class RemoteFunction():
    """Annotate Remote Functions with @RemoteFunction
    Make sure,  that you specify the types for your parameters:

    Valid choices:
    ctypes.c_bool, ctypes.c_byte, ctypes.c_uint64,
    ctypes.c_int64, ctypes.c_double, ctypes.c_char_p

    GOOD:
        foo(x: ctypes._uint64, p: ctypes.c_char_p)
    BAD:
        foo(x,p)

    """
    # Functions are stored as tuple in a dict
    # { "name": (<Function reference>,[<Function name>, <Description>, <Arguments>[]] }
    remote_functions = {}

    # The values are picked to avoid confusion between types!
    _default_arg_values = {ctypes.c_bool: False,
                           ctypes.c_byte: b'',  # msgpack packs bytes
                           ctypes.c_uint64: 3,  # msgpack packs an uint
                           ctypes.c_int64: -1,  # msgpack packs an int
                           ctypes.c_double: 2.0,  # msgpack packs float
                           ctypes.c_char_p: "",  # msgpack packs bytes
                           ctypes.c_long: -1}  # msgpack packs an int

    def __init__(self, function: FunctionType):
        # Make sure we don't loose valuable information
        self.fun = function
        self.__name__ = function.__name__
        self.__doc__ = function.__doc__
        self.__defaults__ = function.__defaults__
        self.__annotations__ = function.__annotations__
        self.args = []
        argc = function.__code__.co_argcount  # number of arguments

        argtypes = function.__annotations__
        if len(argtypes) != argc and argc != 0:
            return  # invalid function.

        if len(argtypes) != 0:
            argnames = function.__code__.co_varnames[:argc]
            for n in argnames:
                arg = self._default_arg_values.get(argtypes[n])
                if arg is None:
                    return  # invalid function
                self.args.append(arg)

        if self.__doc__ is None:
            doc = ""
        else:
            doc = self.__doc__

        # Add function to dict of remote functions
        RemoteFunction.remote_functions[self.__name__] = (
            self, [self.__name__, doc, self.args])

    def __call__(self, *args, **kwargs):
        args = args[0]
        if len(self.args) != len(args):
            raise TypeError()

        for i in range(len(self.args)):
            if self.args[i] == "":
                args[i] = args[i].decode('ascii')

        return self.fun(*args)
