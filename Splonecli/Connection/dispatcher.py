import types
from Splonecli.Api.apicall import Apicall
from Splonecli.Connection.message import MRequest


class Dispatcher:
    def __init__(self):
        self._functions = {}
        pass

    def flush_functions(self):
        self._functions = {}

    def register_function(self, foo):
        assert(isinstance(foo, (types.FunctionType, types.MethodType)))
        assert (self._functions.get(foo.__name__) is None)
        self._functions[foo.__name__] = foo
        pass

    def dispatch(self, msg: MRequest):
        call = Apicall.from_Request(msg)
        if call.request.method == "run":
            self._handle_run(call.get_method_name(), call.get_method_args())
        else:
            pass # Insert error handling here

    def _handle_run(self, function_name: str, args: []):
        function = self._functions.get(function_name)
        assert (function is not None)
        function(*args)
        pass
