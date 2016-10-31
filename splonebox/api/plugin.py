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
from threading import Thread, ThreadError
from types import FunctionType

from splonebox.rpc.message import MRequest, InvalidMessageError
from splonebox.api.apicall import ApiRun, ApiResult, ApiRegister
from splonebox.api.remotefunction import RemoteFunction
from splonebox.api.core import Core


class Plugin:
    def __init__(self, name: str, desc: str, author: str, licence: str, core:
                 Core):
        """
        :param name: Name of the plugin
        :param desc: Description of the plugin
        :param author: Author of the plugin
        :param licence: License of the plugin
        :param debug: If true more information will be printed to the output
        :param serverlongtermpk: The server's longterm key
        (if set, path is ignored!)
        :param serverlongtermpk_path: path to file containing the
        server's longterm key
        """
        # [<name>, <description>, <author>, <license>]
        self._metadata = [name, desc, author, licence]
        self.function_meta = {}

        # active threads
        self._active_threads = {int: Thread()}

        core.set_run_handler(self._handle_run)
        self.core = core

        # A dict containing all functions this plugin wants to register
        self.functions = {}

        for f in RemoteFunction.remote_functions:
            self.functions[f.__name__] = f
            self.function_meta[f.__name__] = [f.__doc__, f.args]

    def add_function(self, func: FunctionType):
        """ Manually add a function to the plugin
        (Note: Functions with the @RemoteFunction decorator are
        added automatically)
        """
        f = RemoteFunction(func)
        self.functions[f.__name__] = f
        self.function_meta[f.__name__] = [f.__doc__, f.args]

    def register(self, blocking=True):
        """Registers the Plugin and all annotated functions @ the core.
        This call is blocking

        :raises :InvalidApiCallError if something is wrong with the metadata
        or functions
        :raises :BrokenPipeError if something is wrong with the connection
        :raises :RemoteError if the register call was invalid
        """
        fun_meta = [[k, v[0], v[1]] for k, v in self.function_meta.items()]
        reg_call = ApiRegister(self._metadata, fun_meta)

        result = self.core.send_register(reg_call)

        if blocking:
            result.await()
            return
        else:
            return result

    def _handle_run(self, msg: MRequest):
        """Callback to handle run requests

        :param msg: Message containing run Request (MRequest)
        """
        # TODO: Verify call id!?

        try:
            call = ApiRun.from_msgpack_request(msg)
        except InvalidMessageError:
            return [400, "Message is not a valid run call"], None

        try:
            fun = self.functions[call.get_method_name()]
        except KeyError:
            return [404, "Function does not exist!"], None

        # start new thread for call. TODO: Implement stop API call
        try:
            t = Thread(target=self._execute_function,
                       args=(fun,
                             call.get_method_args(),
                             msg.arguments[0][1], ))
            t.start()
            # store active process
            self._active_threads[msg.arguments[0][1]] = t

        except ThreadError:
            # Error handling on API -level
            pass

        return None, [msg.arguments[0][1]]

    def _execute_function(self, fun, args, call_id):
        try:
            result = fun(args)
            if result is None:
                return

            result_call = ApiResult(call_id, result)

            self.core.send_result(result_call)

            # TODO: Error handling on API-level (not discussed yet -
            # errors will be ignored)!
        except TypeError as e:
            logging.error("ERROR: " + e.__str__())
            pass
        except Exception as e:
            logging.error("ERROR: " + e.__str__())
            pass


class PluginError(Exception):
    pass
