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
from splonebox.api.apicall import ApiResult, InvalidApiCallError
from splonebox.api.result import Result, RunResult, RegisterResult


class Core():
    def __init__(self):
        self._rpc = MsgpackRpc()
        self._responses_pending = {int: Result()}
        self._results_pending = {int: Result()}  # call_id: result

    def enable_debugging(self):
        logging.basicConfig(level=logging.INFO)

    def connect(self, addr: str, port: int):
        """ Connect to the splonebox core
        :param addr: server address
        :param port: Host's port
        """
        self._rpc.connect(addr, port)

    def send_run(self, msg):
        """Sends a message to the server
        :param msg Request or response
        :param callback None if msg is a Response.
        Callback for a response if msg is a request
        """
        result = RunResult()
        self._responses_pending[msg.get_msgid()] = result
        self._rpc.send(msg, self._handle_run_response)
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

    def send_result(self, msg):
        logging.info("Sending result: " + msg.__str__())
        self._rpc.send(msg, callback=self._handle_result_response)

    def _handle_result_response(self, msg: MResponse):
        logging.info("Result request successfull")
        # TODO: Discuss error handling on invalid result request

    def send_register(self, msg):
        result = RegisterResult()
        self._responses_pending[msg.get_msgid()] = result
        self._rpc.send(msg, self._handle_register_response)
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
            self.send_error_response(msg.get_msgid(), 400,
                                     "Message is not a valid result call")
            return
        try:
            self._results_pending[result_call.get_call_id()].set_result(
                result_call.get_result())
            # TODO: error handling
            self.send_success_response(msg.get_callid(),
                                       [result_call.get_call_id()])
            self._results_pending.pop(result_call.get_call_id())
        except KeyError:
            self.send_error_response(msg.get_msgid(), 404,
                                     "Call id does not match any call")

    def send_error_response(self, msgid: int,
                            error_code: int, error_string: str):
        msg = MResponse(msgid)
        msg.error = [error_code, error_string]
        msg.response = None
        self._rpc.send(msg)

    def send_success_response(self, msgid: int,  response: []):
        msg = MResponse(msgid)
        msg.error = None
        msg.response = response
        self._rpc.send(msg)

    def listen(self):
        """Listen for incoming messages from server"""
        self._rpc.listen()

    def disconnect(self):
        """Disconnect from server"""
        self._rpc.disconnect()


class CoreError(Exception):
    pass
