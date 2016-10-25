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
from queue import Queue


class Subscription():
    #  TODO: Proper handling for multiprocessing etc..
    def __init__(self, name: str):
        self.name = name
        self._evt_queue = Queue()

    def wait(self, timeout=None):
        return self._evt_queue.get(timeout=timeout)

    def signal(self, val: []):
        self._evt_queue.put(val)
