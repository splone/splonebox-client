from queue import Queue
from Splonecli.Rpc.message import MResponse, InvalidMessageError, MRequest
from Splonecli.Rpc.msgpackrpc import MsgpackRpc
from Splonecli.Api.apicall import ApiRegister, ApiRun, Apicall, InvalidApiCallError
from Splonecli.Api.remotefunction import RemoteFunction


class Plugin:
    def __init__(self, api_key: str, name: str, desc: str, author: str,
                 licen: str):
        RemoteFunction.remote_functions["stop"] = (self._stop, ["stop", "terminates the plugin", []])

        # [<api key>, <name>, <description>, <author>, <license>]
        self.metadata = [api_key, name, desc, author, licen]
        self._rpc = MsgpackRpc()
        self._rpc.register_function(self._handle_run, "run")
        self._result_queue = Queue(maxsize=1)  # TODO: Is there a better way? This is for SYNCHRONOUS calls!
        self.callbacks = {}

    def connect(self, name: str, port: int):
        """
        Connects to given host

        :param name: (ip/web address)
        :param port: Host's Port
        :return:
        """
        self._rpc.connect(name, port)

    def register(self):
        """
        Registers the Plugin and all annotated functions @ the core.
        -> Make sure you are connected

        :return: None
        """
        assert (None not in self.metadata)
        # Register functions remotely
        # all we need is the function's metadata
        functions = []
        for name, inf in RemoteFunction.remote_functions.items():
            functions.append(inf[1])
        # Create a register call
        reg = ApiRegister(self.metadata, functions)
        self._rpc.send(reg.msg)  # send the msgpack-rpc formatted message

    def _handle_response(self, result):
        self._result_queue.put(result)

    def run(self, api_key: str, function: str, arguments: []):
        """
        Run a remote function and synchronously wait for a result
        :param api_key: Target? api_key
        :param function: name of the function
        :param arguments: function arguments
        :return: result (This is currently a synchronous call!)
        """
        self._rpc.send(ApiRun(api_key, function, arguments).msg, self._handle_response)
        # Okay, remember: This is a synchronous call!
        return self._result_queue.get()

    def wait(self):
        """
        Waits until the connection is closed

        :return:
        """
        self._rpc.wait()

    def _stop(self, *args, **kwargs):
        self._rpc.disconnect()

    def _handle_run(self, msg: MRequest):
        # TODO: Make sure this is a valid Request!
        try:
            call = Apicall.from_Request(msg)
        except InvalidApiCallError as e:
            raise InvalidMessageError(e.__str__())

        fun = RemoteFunction.remote_functions[call.get_method_name()][0]

        try:
            ret = fun(call.get_method_args())
        except Exception as e:
            raise InvalidMessageError("ERROR! Unable to call function (" + call.get_method_name() + "): " + e.__str__())

        # TODO: Handle return ?
        result = MResponse(msg.get_msgid())
        result.body = [ret]
        self._rpc.send(result)

