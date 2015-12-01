from types import FunctionType

from Splonecli.Api.apicall import ApiRegister, ApiRun
from Splonecli.Connection.connection import Connection
from Splonecli.Connection.dispatcher import Dispatcher


class Plugin:
    # Functions are stored as tuple (<Function reference>,[<Function name>, <Description>, <Arguments>[]])
    remote_functions = []

    def __init__(self, apikey: str, name: str, desc: str, author: str, licen: str):
        # [<api key>, <name>, <description>, <author>, <license>]
        self.metadata = [apikey, name, desc, author, licen]
        self._connection = Connection()
        self._dispatcher = Dispatcher()
        self._connection.set_dispatcher(self._dispatcher)

    def connect(self, name: str, port: int):
        """
        Connects to given host

        :param name: (ip/web address)
        :param port: Host's Port
        :return:
        """
        # TODO: Error handling?
        self._connection.connect(name, port)

    def register(self):
        """
        Registers the Plugin and all annotated functions @ the core.
        -> Make sure you are connected

        :return: None
        """
        assert (None not in self.metadata and self._connection.connected)
        # all we need is the function's metadata
        functions = list(map(lambda f: f[1], Plugin.remote_functions))

        # Create a register object
        reg = ApiRegister(self.metadata, functions)

        # Transform register to request message
        self._connection.send_message(reg.request)

        # Make sure the dispatcher doesn't get confused (That poor thing :'(.. )
        self._dispatcher.flush_functions()
        # Register the functions @ our local dispatcher
        for fun in Plugin.remote_functions:
            self._dispatcher.register_function(fun[0])

    def run(self, apikey: str, functionname: str, arguments: []):
        """
        Sends a run request to the core

        :param apikey: ?remote? plugins api key
        :param functionname: remote function name
        :param arguments:  remote function arguments
        :return:
        """
        self._connection.send_message(ApiRun(apikey, functionname, arguments).request)

    def wait(self):
        """
        Waits until the connection is closed

        :return:
        """
        self._connection.is_listening.acquire()


class RemoteFunction(object):
    """
    Annotate Remote Functions with @RemoteFunction and import Plugin.RemoteFunction

    Make sure,  that your remote functions have defaullt values for their parameters
    ( Add other options?)

    GOOD:
        foo(x = 0, p = "")
    BAD:
        foo(x,p)
    """

    def __init__(self, function: FunctionType):
        # TODO: Is there a better way to handle this?
        # Make sure we don't use valuable information
        self.fun = function
        self.__name__ = function.__name__
        self.__doc__ = function.__doc__
        self.__defaults__ = function.__defaults__

        args = []
        if function.__defaults__ is not None:
            args = list(function.__defaults__)
            assert (len(args) == function.__code__.co_argcount)
        else:
            assert (function.__code__.co_argcount == 0)

        doc = function.__doc__
        if doc is None:
            doc = ""

        # TODO: Is there a better way to communicate between thse two modules?
        Plugin.remote_functions.append((function, [function.__name__, doc, args]))

    def __call__(self, *args, **kwargs):
        # TODO: Should it be possible to call a remote function locally?
        print("You are calling a remote function locally!")
        self.fun(*args)

