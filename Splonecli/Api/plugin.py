import logging
from queue import Queue

import sys

from Splonecli.Rpc.message import MResponse, MRequest, InvalidMessageError
from Splonecli.Rpc.msgpackrpc import MsgpackRpc
from Splonecli.Api.apicall import ApiRegister, ApiRun
from Splonecli.Api.remotefunction import RemoteFunction


class Plugin:
	def __init__(self, api_key: str, name: str, desc: str, author: str,
				 licence: str, debug=False):

		# register stop function
		RemoteFunction.remote_functions["stop"] = (
			self._stop, ["stop", "terminates the plugin", []])

		# [<api key>, <name>, <description>, <author>, <license>]
		self._metadata = [api_key, name, desc, author, licence]

		self._rpc = MsgpackRpc()
		# register run function @ rpc dispatcher
		self._rpc.register_function(self._handle_run, "run")

		# initialize queue for synchronous calls
		self._result_queue = Queue(maxsize=1)  # TODO: Is there a better way?

		# set logging level
		if debug:
			logging.basicConfig(level=logging.INFO)
		logging.info("Plugin object created..\n")

	def connect(self, name: str, port: int):
		# Note: This wraps Connection.connect(name,port)
		"""
		Connects to given host

		:param name: (ip/web address)
		:param port: Host's Port
		:return:
		:raises: :ConnectionRefusedError if socket is unable to connect
		:raises: socket.gaierror if Host unknown
		:raises: :ConnectionError if hostname or port are invalid types
		"""
		self._rpc.connect(name, port)

	def register(self):
		"""
		Registers the Plugin and all annotated functions @ the core.
		-> Make sure you are connected

		:return: None
		"""

		# Register functions remotely
		# all we need is the function's metadata
		functions = []
		for name, inf in RemoteFunction.remote_functions.items():
			functions.append(inf[1])
		# Create a register call

		reg = ApiRegister(self._metadata, functions)

		self._rpc.send(reg.msg)  # send the msgpack-rpc formatted message

	def _handle_response(self, result: MResponse):
		"""
		Default function for handling responses (Synchronous calls!)
		:param result: Response Message containing result/error
		:return:
		"""
		self._result_queue.put(result)

	def run(self, api_key: str, function: str, arguments: [], has_result=True):
		"""
		Run a remote function and synchronously wait for a result

		:param has_result: Does the called function have a result?
		:param api_key: Target? api_key
		:param function: name of the function
		:param arguments: function arguments | empty list or None for no args
		:return: result (This is currently a synchronous call!)
		"""
		if has_result:
			self._rpc.send(ApiRun(api_key, function, arguments).msg,
						   self._handle_response)
			# Okay, remember: This is a synchronous call!
			return self._result_queue.get()
		else:
			self._rpc.send(ApiRun(api_key, function, arguments).msg, None)

	def listen(self):
		"""
		Waits until the connection is closed
		"""
		self._rpc.wait()

	def _stop(self, *args, **kwargs):
		self._rpc.disconnect()

	def _handle_run(self, msg: MRequest):
		"""
		Callback to handle run requests
		:param msg: Message containing run Request (MRequest)
		:return:
		"""

		# errors are handled by MsgpackRpc._message_callback

		response = MResponse(msg.get_msgid())

		try:
			call = ApiRun.from_msgpack_request(msg)
		except InvalidMessageError:
			response.error= [400, "Received Message is not a valid run call"]
			self._rpc.send(response)
			return

		try:
			fun = RemoteFunction.remote_functions[call.get_method_name()][0]
		except KeyError:
			response.error =[404, "Function does not exist!"]
			self._rpc.send(response)
			return

		try:
			fun(call.get_method_args())
		except TypeError:
			response.error = [400, "Invalid Argument(s)"]
			self._rpc.send(response)
		except Exception:
			response.error = [420, "Function Execution failed"]
			self._rpc.send(response)
			# TODO: More percise response
			return

class PluginError(Exception):
	def __init__(self, value: str):
		self.value = value

	def __str__(self) -> str:
		return self.value
