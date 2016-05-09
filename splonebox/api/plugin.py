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

import logging

from threading import Thread, ThreadError

from splonebox.rpc.message import MResponse, MRequest, InvalidMessageError
from splonebox.rpc.msgpackrpc import MsgpackRpc
from splonebox.api.apicall import ApiRegister, ApiRun
from splonebox.api.remotefunction import RemoteFunction
from splonebox.api.result import RunResult, Result, RegisterResult


class Plugin:
    def __init__(self,
                 plugin_id: str,
                 name: str,
                 desc: str,
                 author: str,
                 licence: str,
                 debug=False):
        """
        :param plugin_id: api key (make sure it was added to the core)
        :param name: Name of the plugin
        :param desc: Description of the plugin
        :param author: Author of the plugin
        :param licence: License of the plugin
        :param debug: If true more information will be printed to the output
        :param serverlongtermpk: The server's longterm key
        (if set, path is ignored!)
        :param serverlongtermpk_path: path to file containing the
        server's longterm key
        """
        # [<plugin_id>, <name>, <description>, <author>, <license>]
        self._metadata = [plugin_id, name, desc, author, licence]

        self._rpc = MsgpackRpc()
        # register run function @ rpc dispatcher
        self._rpc.register_function(self._handle_run, "run")

        # pending_responses
        self._responses_pending = {int: Result()}  # msgid: result
        # pending_results
        self._results_pending = {int: Result()}  # call_id: result
        # active threads
        self._active_threads = {int: Thread()}

        # set logging level
        if debug:
            logging.basicConfig(level=logging.INFO)
        logging.info("Plugin object created..\n")

    def connect(self, name: str, port: int):
        # Note: This wraps Connection.connect(name,port)
        """Connects to given host

        :param name: (ip/web address)
        :param port: Host's Port
        :raises: :ConnectionRefusedError if socket is unable to connect
        :raises: socket.gaierror if Host unknown
        :raises: :ConnectionError if hostname or port are invalid types
        """
        self._rpc.connect(name, port)

    def register(self, blocking=True):
        """Registers the Plugin and all annotated functions @ the core.

        :raises :InvalidApiCallError if something is wrong with the metadata
                 or functions
        :raises :BrokenPipeError if something is wrong with the connection
        :raises :RemoteError if the register call was invalid
        :returns :RegisterResult if non blocking
        """
        # Register functions remotely
        # all we need is the function's metadata
        functions = []
        for name, inf in RemoteFunction.remote_functions.items():
            functions.append(inf[1])
        # Create a register call

        reg = ApiRegister(self._metadata, functions)

        # send the msgpack-rpc formatted message
        self._rpc.send(reg.msg, self._handle_response)
        result = RegisterResult()
        self._responses_pending[reg.msg.get_msgid()] = result
        if blocking:
            result.await()
        else:
            return result

    def _handle_response(self, response: MResponse):
        """Default function for handling responses

        :param responset: Response Message containing response/error
        """
        result = self._responses_pending.pop(response.get_msgid())
        if response.error is not None:
            result.set_error([response.error[0], response.error[1].decode(
                'ascii')])
        else:
            if result.get_type() == 0:
                # We received a response for a register call
                if response.error is None and response.response == []:
                    result.success()
                else:
                    result.set_error([400, "Received invalid Response"])
            elif result.get_type() == 1:
                # we received a response for a run call
                result.set_id(response.response[0])
                self._results_pending[result.get_id()] = result

    def run(self, plugin_id: str, function: str, arguments: []):
        """Run a remote function and return a :Result

        :param has_result: Does the called function have a result?
        :param plugin_id: Targets plugin_id
        :param function: name of the function
        :param arguments: function arguments | empty list or None for no args
        :return: :RunResult
        :raises :RemoteRunError if run call failed
        """
        run_call = ApiRun(plugin_id, function, arguments)
        self._rpc.send(run_call.msg, self._handle_response)

        result = RunResult()
        self._responses_pending[run_call.msg.get_msgid()] = result
        return result

    def listen(self):
        """Waits until the connection is closed"""
        self._rpc.listen()

    def stop(self):
        """Stops the plugin"""
        self._rpc.disconnect()

    def _handle_run(self, msg: MRequest):
        """Callback to handle run requests

        :param msg: Message containing run Request (MRequest)
        """

        response = MResponse(msg.get_msgid())
        # TODO: Verify call id!

        try:
            call = ApiRun.from_msgpack_request(msg)
        except InvalidMessageError:
            response.error = [400, "Received Message is not a valid run call"]
            self._rpc.send(response)
            return

        try:
            fun = RemoteFunction.remote_functions[call.get_method_name()][0]
        except KeyError:
            response.error = [404, "Function does not exist!"]
            self._rpc.send(response)
            return

        # Send execution validation
        response.response = [msg.arguments[0][1]]
        self._rpc.send(response)

        # start new thread for call. Implement stop API call
        try:
            t = Thread(target=self._execute_function,
                       args=(fun,
                             call.get_method_args(),
                             msg.arguments[0][1], ))
            t.start()
            # store active process
            self._active_threads[msg.arguments[0][1]] = t

        except ThreadError:
            # Error handling on API -level
            pass

    def _execute_function(self, fun, args, call_id):
        msg_result = MRequest()
        msg_result.function = "result"
        try:
            result = fun(args)
            # Send Result
            msg_result.arguments = [[call_id], [result]]
            # self._rpc.send(msg_result)
            logging.info("Would send result: " + msg_result.__str__())
        # TODO: Error handling on API-level (not discussed yet - errors will be
        # ignored!)
        except TypeError:
            pass
        except Exception:
            pass


class PluginError(Exception):
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value
