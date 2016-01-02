import ctypes
from types import FunctionType


class RemoteFunction(object):
    """
    Annotate Remote Functions with @RemoteFunction and import Plugin.RemoteFunction


    Make sure,  that you specify the types for your parameters:


    Valid choices:
     ctypes.c_bool, ctypes.c_byte, ctypes.c_uint64, ctypes.c_int64, ctypes.c_double, ctypes.c_char_p

    GOOD:
        foo(x: ctypes._uint64, p: ctypes.c_char_p)
    BAD:
        foo(x,p)

    """
    # Functions are stored as tuple
    # (<Function reference>,[<Function name>, <Description>, <Arguments>[]])
    remote_functions = {}

    _default_arg_values = {ctypes.c_bool: False,
                           ctypes.c_byte: "",
                           ctypes.c_uint64: 0,  # msgpack packs an uint
                           ctypes.c_int64: -1,  # msgpack packs an int
                           ctypes.c_double: 0.0,
                           ctypes.c_char_p: "",
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
        assert (len(argtypes) == argc or argc == 0)
        if len(argtypes) != 0:
            print(argtypes)
            argnames = function.__code__.co_varnames[:argc]
            for n in argnames:
                arg = self._default_arg_values.get(argtypes[n])
                assert (arg is not None)
                self.args.append(arg)

        if self.__doc__ is None:
            doc = ""
        else:
            doc = self.__doc__

        #  Add function to dict of remote functions
        self.remote_functions[self.__name__] = (self, [self.__name__, doc, self.args])

    def __call__(self, *args, **kwargs):
        return self.fun(*args[0])

