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

from splonebox.api.core import Core, CoreError
from splonebox.api.plugin import Plugin
from splonebox.api.result import RunResult
from splonebox.api.apicall import ApiRun
from splonebox.api.subscription import Subscription

import signal
import sys
import logging


__core = None
__plugin = None


def _handler(signal, handler):
    global __core
    logging.warning("CTRL-C was pressed.. Shutting down")
    if __core is not None:
        __core.disconnect()
    sys.exit(0)

signal.signal(signal.SIGINT, _handler)


def enable_debugging():
    logging.basicConfig(level=logging.INFO)

def connect(addr: str, port: int):
    global __core
    __core = Core()
    __core.connect(addr, port)


def disconnect():
    global __core, __plugin
    if __core is None:
        raise CoreError("Core not inited - You need to call connect(..) first")
    __core.disconnect()
    __core = None
    __plugin = None


def register(name: str, desc: str, author: str, licence: str):
    global __core, __plugin
    if __core is None:
        raise CoreError("Core not inited - You need to call connect(..) first")

    __plugin = Plugin(name, desc, author, licence, __core)
    __plugin.register()


def broadcast(event_name: str, args: []):
    global __core
    if __core is None:
        raise CoreError("Core not inited - You need to call connect(..) first")
    __core.broadcast(event_name, args)


def subscribe(event_name: str) -> Subscription:
    global __core
    if __core is None:
        raise CoreError("Core not inited - You need to call connect(..) first")

    return __core.subscribe(event_name)


def unsubscribe(event_name: str, blocking=True):
    global __core
    if __core is None:
        raise CoreError("Core not inited - You need to call connect(..) first")

    rsp = __core.unsubscribe(event_name)
    rsp.await()


def send_run(plugin_id: str, function_name: str, args: []) -> RunResult:
    global __core
    if __core is None:
        raise CoreError("Core not inited - You need to call connect(..) first")

    call = ApiRun(plugin_id, function_name, args)
    return __core.send_run(call)
