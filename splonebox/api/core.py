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

from splonebox.rpc.msgpackrpc import MsgpackRpc
from splonebox.rpc.message import MResponse, MRequest, InvalidMessageError
from splonebox.api.apicall import ApiRun, ApiResult
from splonebox.api.apicall import ApiRegister, InvalidApiCallError
from splonebox.api.result import Result, RunResult, RegisterResult


class Core():
    def __init__(self):
        self._rpc = MsgpackRpc()
        self._rpc.register_function(self._handle_result, "result")
        self._responses_pending = {int: Result()}
        self._results_pending = {int: RunResult()}  # call_id: result

    def enable_debugging(self):
        logging.basicConfig(level=logging.INFO)

    def connect(self, addr: str, port: int):
        """ Connect to the splonebox core
        :param addr: server address
        :param port: Host's port
        """
        self._rpc.connect(addr, port)

    def listen(self):
        """Listen for incoming messages from server"""
        self._rpc.listen()

    def disconnect(self):
        """Disconnect from server"""
        self._rpc.disconnect()

    def set_run_handler(self, function):
        """ Set the function to be called on incomming run requests """
        self._rpc.register_function(function, "run")

    def send_run(self, call: ApiRun):
        """Sends a message to the server
        :param msg Request or response
        :param callback None if msg is a Response.
        Callback for a response if msg is a request
        """
        result = RunResult()
        self._responses_pending[call.msg.get_msgid()] = result
        self._rpc.send(call.msg, self._handle_run_response)
        return result

    def _handle_run_response(self, msg: MResponse):
        """Default function for handling responses

        :param responset: Response Message containing response/error
        """
        result = self._responses_pending.pop(msg.get_msgid())

        if msg.error is not None:
            result.set_error([msg.error[0], msg.error[1].decode(
                'ascii')])
        else:
            # we received a response for a run call
            result.set_id(msg.response[0])
            self._results_pending[result.get_id()] = result

    def send_result(self, call: ApiResult):
        """Send a result API call to the server"""
        logging.info("Sending result: " + call.msg.__str__())
        self._rpc.send(call.msg,
                       response_callback=self._handle_result_response)

    def _handle_result_response(self, msg: MResponse):
        logging.info("Result request successfull")
        # TODO: Discuss error handling on invalid result request

    def send_register(self, call: ApiRegister):
        """Send a register API call to the server"""
        result = RegisterResult()
        self._responses_pending[call.msg.get_msgid()] = result
        self._rpc.send(call.msg, self._handle_register_response)
        return result

    def _handle_register_response(self, msg: MResponse):
        result = self._responses_pending.pop(msg.get_msgid())
        if msg.error is not None:
            result.set_error([msg.error[0], msg.error[1].decode('ascii')])
        else:
            if msg.error is None and msg.response == []:
                result.success()
            else:
                result.set_error([400, "Received invalid Response"])

    def _handle_result(self, msg: MRequest):
        try:
            result_call = ApiResult.from_msgpack_request(msg)
        except (InvalidApiCallError, InvalidMessageError):
            return ([400, "Message is not a valid result call"], None)
        try:
            self._results_pending[result_call.get_call_id()].set_result(
                result_call.get_result())
            # TODO: error handling
            return (None, [result_call.get_call_id()])
            # self._results_pending.pop(result_call.get_call_id())
        except KeyError:
            return ([404, "Call id does not match any call"], None)


class CoreError(Exception):
    pass
