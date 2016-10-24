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
from threading import Event
import datetime


class Response():
    """An object representing the Response to a call."""
    def __init__(self):
        self._error = None
        self._event = Event()
        self.init_ts = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        self.fin_ts = -1
        self.called_function = None
        self.called_by_id = None
        self.call_arguments = None

    def set_error(self, error: []):
        if not isinstance(error,
                          list) or not len(error) == 2 or not isinstance(
                              error[0], int) or not isinstance(error[1], str):
            raise RemoteError(400, "Invalid error result!")
        self._error = error
        self.fin_ts = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        self._event.set()

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
        self.fin_ts = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        self._event.set()


class RemoteError(Exception):
    def __init__(self, errno: int, name: str):
        self.errno = errno
        self.name = name

    def __str__(self) -> str:
        return "Error " + self.errno + ": " + self.name
