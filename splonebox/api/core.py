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
from splonebox.rpc.message import MResponse, MRequest, MNotify
from splonebox.rpc.message import InvalidMessageError
from splonebox.api.apicall import ApiRun, ApiResult, ApiBroadcast
from splonebox.api.apicall import ApiSubscribe, ApiUnsubscribe
from splonebox.api.apicall import ApiRegister, InvalidApiCallError
from splonebox.api.response import Response
from splonebox.api.result import RunResult
from splonebox.api.subscription import Subscription


class Core():
    def __init__(self):
        self._rpc = MsgpackRpc()
        self._rpc.register_function(self._handle_result, "result")
        self._rpc.register_function(self._handle_broadcast, "broadcast")
        self._responses_pending = {int: Response()}
        self._results_pending = {int: RunResult()}  # call_id: result
        self._subscriptions = {}
        self.connected = False

    def enable_debugging(self):
        logging.basicConfig(level=logging.INFO)

    def connect(self, addr: str, port: int):
        """ Connect to the splonebox core
        :param addr: server address
        :param port: Host's port
        """
        self._rpc.connect(addr, port)
        self.connected = True

    def listen(self):
        """Listen for incoming messages from server"""
        self._rpc.listen()

    def disconnect(self):
        """Disconnect from server"""
        self._rpc.disconnect()
        self.connected = False

    def set_run_handler(self, function):
        """ Set the function to be called on incomming run requests """
        self._rpc.register_function(function, "run")

    def send_run(self, call: ApiRun):
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
            result.set_error([msg.error[0], msg.error[1].decode('ascii')])
        else:
            # we received a response for a run call
            result.set_id(msg.response[0])
            self._results_pending[result.get_id()] = result

    def send_result(self, call: ApiResult):
        """Send a result API call to the server"""
        self._rpc.send(call.msg,
                       response_callback=self._handle_result_response)

    def _handle_result_response(self, msg: MResponse):
        logging.info("Result request successfull")
        # TODO: Discuss error handling on invalid result request

    def send_register(self, call: ApiRegister):
        """Send a register API call to the server"""
        response = Response()
        self._responses_pending[call.msg.get_msgid()] = response
        self._rpc.send(call.msg, self._handle_response)
        return response

    def _handle_response(self, msg: MResponse):
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

    def broadcast(self, event_name: str, args: [], as_notification=True):
        """ If as_notification is false this returns a response """
        call = ApiBroadcast(event_name, args, as_notification)
        if as_notification:
            self._rpc.send(call.msg)
            return None
        else:
            response = Response()
            self._responses_pending[call.msg.get_msgid()] = response
            self._rpc.send(call.msg, response=self._handle_response)
            return response

    def subscribe(self, event_name: str):
        sub = Subscription(event_name)
        #  TODO: a subscription for the given event might already exist
        self._subscriptions[event_name] = sub
        call = ApiSubscribe(event_name)
        response = Response()
        self._responses_pending[call.msg.get_msgid()] = response
        self._rpc.send(call.msg, response_callback=self._handle_response)
        response.await()
        return sub

    def unsubscribe(self, event_name: str):
        self._subscriptions.pop(event_name)

        #  TODO: subscirbe callback
        call = ApiUnsubscribe(event_name)
        response = Response()
        self._responses_pending[call.msg.get_msgid()] = response
        #  TODO: subscirbe callback
        self._rpc.send(call.msg, response_callback=self._handle_response)
        return response

    def _handle_broadcast(self, msg: MNotify):
        if not msg.get_type() == 2:
            logging.warning("Broadcast handler received a Request ")
            return
        try:
            subs = self._subscriptions[msg.function]
            subs.signal(msg.arguments)
            logging.info("received event: " + msg.arguments.__str__())
        except KeyError:
            logging.warning("Received an event that we haven't subscribed to")
            return


class CoreError(Exception):
    pass
