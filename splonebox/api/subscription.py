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
from threading import Event


class Subscription():
    #  TODO: Proper handling for multiprocessing etc..
    def __init__(self, name: str):
        self.name = name
        self._event = Event()
        self._val = []

    def wait(self, timeout=None):
        #  TODO: Think of some fancy synchro stuff
        self._event.wait(timeout)
        return self._val

    def signal(self, val: []):
        self._val.append(val)
        self._event.set()
        self._event.clear()
