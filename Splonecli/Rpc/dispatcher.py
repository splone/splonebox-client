from Splonecli.Rpc.message import MRequest, InvalidMessageError


class Dispatcher:
    def __init__(self):
        self._functions = {}
        pass

    def flush_functions(self):
        self._functions = {}

    def register_function(self, fun, name: str):
        """
        Register a function
        :param fun: A function that takes one argument of type MRequest
        :param name: The name of the function
        :return:
        """
        if self._functions.get(name) is not None:
            raise DispatcherError("Function already registered!")
        self._functions[name] = fun

    def dispatch(self, msg: MRequest):
        """
        calls the function mentioned in the given request,
        raises error if the function is not registered at the dispatcher

        :param msg:
        :return:
        """
        if msg.method not in self._functions:
            raise InvalidMessageError("Function not available: " + msg.method)
        try:
            self._functions[msg.method](msg)
        except InvalidMessageError as e:
            raise InvalidMessageError("Request: " + msg.method + "\n" + e.value)


class DispatcherError(Exception):
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name
