import logging

import msgpack

from Splonecli.Rpc.connection import Connection
from Splonecli.Rpc.dispatcher import Dispatcher, DispatcherError
from Splonecli.Rpc.message import Message, InvalidMessageError, MResponse


class MsgpackRpc:
	def __init__(self):
		self._connection = Connection()
		self._dispatcher = Dispatcher()
		self._response_callbacks = {}
		self._unpacker = msgpack.Unpacker()
		pass

	def connect(self, host: str, port: int):
		"""
		:param host:
		:param port:
		:raises: :ConnectionRefusedError if socket is unable to connect
		:raises: socket.gaierror if Host unknown
		:raises: :ConnectionError if hostname or port are invalid types
		"""
		self._connection.connect(host, port, self._message_callback)

	def send(self, msg: Message, response_callback=None):
		"""
		:param msg:
		:param response_callback:
		:raises :InvalidMessageError if msg.pack() is not possible
		:raises :BrokenPipeError if connection is not established
		:return: None
		"""
		logging.info("sending: \n" + msg.__str__())
		if msg is None:
			raise InvalidMessageError("Unable to send None!")
		self._connection.send_message(msg.pack())

		if response_callback is not None:
			self._response_callbacks[msg.get_msgid()] = response_callback
		# if response callback is None we don't expect a response

	def _message_callback(self, data):
		"""

		:param data:
		:return:
		"""
		self._unpacker.feed(data)
		messages = []
		for unpacked in self._unpacker:
			try:
				messages.append(Message.unpack(unpacked))
			except InvalidMessageError:
				m = MResponse(0)
				m.error = [400, "Invalid Message Format"]
				self.send(m)
				pass

		for msg in messages:
			try:
				logging.info('Received this message: \n' + msg.__str__())
				if msg.get_type() == 0:
					# type == 0  => Message is request
					self._dispatcher.dispatch(msg)
				elif msg.get_type() == 1:
					self._handle_response(msg)
				elif msg.get_type() == 2:
					self._handle_notify(msg)

			except InvalidMessageError as e:
				logging.info(e.value)
				logging.info(
					"\n Unable to handle Message\n")

				m = MResponse(msg.get_msgid())
				m.error = [400, "Could not handle request! " + e.value]
				self.send(m)

			except Exception as e:
				logging.warning("Unexpected exception occurred!")
				logging.warning(e.__str__())

				m = MResponse(msg.get_msgid())
				m.error = [418, "Unexpected exception occurred!"]

	def register_function(self, foo, name: str):
		"""
		:param name:
		:param foo: a function reference
		:return:
		"""
		self._dispatcher.register_function(foo, name)

	def disconnect(self):
		self._connection.disconnect()

	def wait(self):
		self._connection.is_listening.acquire()

	def _handle_response(self, msg: MResponse):
		"""

		:param msg:
		:return:
		"""
		try:
			self._response_callbacks[msg.get_msgid()](msg)
			self._response_callbacks.pop(msg.get_msgid())
		except Exception:
			if msg.error is not None:
				logging.warning(
					"Received error unrelated to any message!\n"
					+ msg.error.__str__())
			else:
				logging.warning(
					"The msgid in given response does not match any request!\n")

			raise
		pass

	def _handle_notify(self, msg):
		"""
			Notfify Messages are ignored for now
			:param msg:
			:return:
			"""
		pass
