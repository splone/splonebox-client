import logging
import socket
from _thread import start_new_thread
from multiprocessing import Lock


class Connection:
	def __init__(self):
		self._buffer_size = pow(1024, 2)  # This is defined my msgpack
		self._ip = None
		self._port = None
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._connected = False
		self.is_listening = Lock()

	def connect(self, hostname: str, port: int, msg_callback, listen=True):
		"""
		Connect to given host
		:param msg_callback: This function gets called on incoming messages. It has one argument of type Message
		:param hostname: hostname
		:param port: port

		:raises: :ConnectionRefusedError if socket is unable to connect
		:raises: socket.gaierror if Host unknown
		:raises: :ConnectionError if hostname or port are invalid types

		:return:
		"""

		if not isinstance(hostname, str):
			raise ConnectionError("Hostname has to be string")

		self._ip = socket.gethostbyname(hostname)

		if not isinstance(port, int) or port <= 0 or port > 65535:
			raise ConnectionError("Port has to be an unsigned 16bit integer")

		self._port = port
		logging.info("Connecting to host: " + hostname + ":" + port.__str__())
		self._socket.connect((self._ip, self._port))
		logging.info("Connected to: " + self._ip + ":" + port.__str__())

		self._connected = True

		if listen:
			self.listen(msg_callback)

	def listen(self, msg_callback, new_thread=True):
		if(new_thread):
			start_new_thread(self._listen, (msg_callback,))
		else:
			self._listen(msg_callback)

		logging.info("Startet listening..")

	def disconnect(self):
		"""
		Closes the socket
		:return:
		"""
		self._connected = False
		self._socket.close()

	def send_message(self, msg: bytes):
		"""
		:raises: BrokenPipeError
		:param msg:
		:return:
		"""
		self._socket.send(msg)

	def _listen(self, msg_callback):
		"""
		Listens for incoming messages.
		:raises: ConnectionError if connection is unexpectedly terminated
		:return:
		"""

		self.is_listening.acquire(True)  # Use this to keep Plugin running
		while True and self._connected:
			try:
				data = self._socket.recv(self._buffer_size)
			except socket.error:
				if self._connected:
					raise

				self.is_listening.release()
				return
			# let the callback handle the received data
			msg_callback(data)

		self.is_listening.release()  # Tell everyone we are done

	def is_connected(self) -> bool:
		"""
		:return: True if connected, False if not
		"""
		return self._connected
