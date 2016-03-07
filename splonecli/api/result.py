import logging
from threading import Event


class Result():
    def __init__(self):
        self._type = None
        self._error = None
        self._event = Event()

    def set_error(self, error: []):
        if not isinstance(error,
                          list) or not len(error) == 2 or not isinstance(
                              error[0], int) or not isinstance(error[1], str):
            raise RemoteError(400, "Invalid error result!")
        self._error = error
        self._event.set()

    def get_type(self):
        return self._type


class RegisterResult(Result):
    """A Result returned by a non blocking register call."""
    def __init__(self):
        super().__init__()
        self._type = 0

    def get_status(self) -> int:
        """ Get call status

        :returns -1 if call failed
        :returns 2 if call was successful
        :returns 0 if there hasn't been a response yet
        """
        if self._error is not None:
            return -1  # register call failed
        elif self._event.is_set():
            return 2  # register call succeeded
        else:
            return 0  # no response yet

    def await(self):
        """Blocking call to wait for register response.

        :raises :RemoteError if register call fails
        """
        self._event.wait()
        if self._error is not None:
            logging.warning("Register call failed!\n" + self._error[0].__str__(
            ) + " : " + self._error[1])
            raise RemoteError(self._error[0], self._error[1])

    def success(self):
        """Signal successful register call

        This will be called by  :Plugin as soon as
        a valid response has been received
        """
        self._event.set()


class RunResult(Result):
    """A Result returned by a run call"""
    def __init__(self):
        super().__init__()
        self._type = 1  # This is a response to a run call
        self._id = None
        self._result = None

    def was_exec(self) -> bool:
        return self._id is not None and self._error is None

    def has_result(self) -> bool:
        return self._event.is_set() or self._error is not None

    def get_status(self) -> int:
        """ Returns the result status

        :returns -1 if call failed
        :returns 1 if function was remotely executed, no result yet
        :returns 2 if call was successful
        :returns 0 if there hasn't been a response yet
        """
        if self._error is not None:
            # Execution failed
            return -1
        elif self._id is None:
            # Message was sent, no response received
            return 0
        elif not self._event.is_set():
            # Currently waiting for result
            return 1
        else:
            # Execution was successful
            return 2

    def get_result(self, blocking=True) -> []:
        """ Returns the actual result of the function

        :param blocking: wait for result
        :returns  Result
        :raises :RemoteError if call failed
        """
        if blocking:
            self._event.wait()
        if self._error is None:
            return self._result
        else:
            logging.info("Run call failed!\n" + self._error[0].__str__() +
                         " : " + self._error[1])
            raise RemoteError(self._error[0], self._error[1])

    def set_result(self, result):
        self._result = result
        self._event.set()

    def get_id(self) -> int:
        return self._id

    def set_id(self, call_id: int):
        self._id = call_id


class RemoteError(Exception):
    def __init__(self, errno: int, name: str):
        self.errno = errno
        self.name = name

    def __str__(self) -> str:
        return "Error " + self.errno + ": " + self.name
