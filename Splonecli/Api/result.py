from threading import Event


class Result():
	def __init__(self):
		self._type = None
		self._error = None
		self._event = Event()

	def set_error(self, error: []):
		self._error = error
		self._event.set()

	def get_type(self):
		return self._type


class RegisterResult(Result):
	def __init__(self):
		super().__init__()
		self._type = 0

	def get_status(self):
		if self._error is not None:
			return -1  # register call failed
		elif self._event.is_set():
			return 2  # register call succeeded
		else:
			return 0  # no response yet

	def await(self):
		self._event.wait()
		return (self.get_status(), self._error)

	def success(self):
		self._event.set()


class RunResult(Result):
	def __init__(self):
		super().__init__()
		self._type = 1  # This is a response to a run call
		self._id = None
		self._result = None

	def was_exec(self):
		return self._id is not None and self._error is None

	def has_result(self) -> bool:
		return self._event.is_set() or self._error is not None

	def get_status(self) -> int:
		if self._error is not None:
			# Execution failed
			return -1
		elif self._id is None:
			# Message was sent, no response received
			return 0
		elif not self._event.is_set():
			# Currently waiting for response
			return 1
		else:
			# Execution was successful
			return 2

	def get_result(self, blocking=True) -> (int, []):
		if blocking:
			self._event.wait()
		if self._error is None:
			return (self.get_status(), self._result)
		else:
			return (-1, self._error)

	def set_result(self, result: []):
		self._result = result
		self._event.set()

	def get_id(self):
		return self._id

	def set_id(self, call_id: int):
		self._id = call_id
