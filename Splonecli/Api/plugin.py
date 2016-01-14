import logging
from Splonecli.Rpc.message import MResponse, MRequest, InvalidMessageError
from Splonecli.Rpc.msgpackrpc import MsgpackRpc
from Splonecli.Api.apicall import ApiRegister, ApiRun
from Splonecli.Api.remotefunction import RemoteFunction
from Splonecli.Api.result import RunResult, Result, RegisterResult


class Plugin:
	def __init__(self,
				 api_key: str,
				 name: str,
				 desc: str,
				 author: str,
				 licence: str,
				 debug=False):
		"""
		:param api_key: Api key (make sure it was added to the core)
		:param name: Name of the plugin
		:param desc: Description of the plugin
		:param author: Author of the plugin
		:param licence: License of the plugin
		:param debug: If true more information will be printed to the output
		"""

		# register stop function
		RemoteFunction.remote_functions["stop"] = (
			self._stop, ["stop", "terminates the plugin", []])

		# [<api key>, <name>, <description>, <author>, <license>]
		self._metadata = [api_key, name, desc, author, licence]

		self._rpc = MsgpackRpc()
		# register run function @ rpc dispatcher
		self._rpc.register_function(self._handle_run, "run")
		self._rpc.register_function(self._handle_result, "result")

		# pending_responses
		self._responses_pending = {int: Result()}  # msgid: result
		# pending_results
		self._results_pending = {int: Result()}  # call_id

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
		:raises: :ConnectionRefusedError if socket is unable to connect
		:raises: socket.gaierror if Host unknown
		:raises: :ConnectionError if hostname or port are invalid types
		"""
		self._rpc.connect(name, port)

	def register(self, blocking=True):
		"""
		Registers the Plugin and all annotated functions @ the core.

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
		"""
		Default function for handling responses (Synchronous calls!)

		:param result: Response Message containing result/error
		"""
		result = self._responses_pending[response.get_msgid()]
		if response.error is not None:
			result.set_error(
				[response.error[0], response.error[1].decode('ascii')])
		else:
			if result.get_type() == 0:
				# We received a response for a register call
				# No actual result expected
				result.success()
			elif result.get_type() == 1:
				# we received a response for a run call
				result.set_id(response.result[0])  # set call id
				self._results_pending[result.get_id()] = result

	def run(self, api_key: str, function: str, arguments: []):
		"""
		Run a remote function and synchronously wait for a result

		:param has_result: Does the called function have a result?
		:param api_key: Target? api_key
		:param function: name of the function
		:param arguments: function arguments | empty list or None for no args
		:return: :RunResult
		:raises :RemoteRunError if run call failed
		"""
		run = ApiRun(api_key, function, arguments)
		self._rpc.send(run.msg, self._handle_response)

		result = RunResult()
		self._responses_pending[run.msg.get_msgid()] = result
		return result

	def listen(self):
		"""
		Waits until the connection is closed
		"""
		self._rpc.listen()

	def _stop(self, *args, **kwargs):
		"""
		Remote function to stop the plugin
		"""
		self._rpc.disconnect()

	def _handle_run(self, msg: MRequest):
		"""
		Callback to handle run requests
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

		try:
			# Send execution validation
			response.result = msg.arguments[0]
			self._rpc.send(response)
			result = fun(call.get_method_args())
			# Send Result
			msg_result = MRequest()
			msg_result.function = "result"
			msg_result.arguments = [msg.arguments[0], [result]]
			self._rpc.send(msg_result)

		except TypeError:
			response.error = [400, "Invalid Argument(s)"]
			self._rpc.send(response)
		except Exception:
			response.error = [420, "Function Execution failed"]
			self._rpc.send(response)
			return

	def _handle_result(self, msg: MRequest):
		# This is not implemented at the server
		# TODO: Implement ApiCall ApiResult!
		self._results_pending[msg.arguments[0][0]].set_result(msg.arguments[1])


class PluginError(Exception):
	def __init__(self, value: str):
		self.value = value

	def __str__(self) -> str:
		return self.value
