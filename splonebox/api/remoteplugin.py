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
from splonebox.api.apicall import ApiRun
from splonebox.api.result import RunResult
from splonebox.api.core import Core

import logging

class RemotePlugin:

    def __init__(self,
                 id: str,
                 name: str,
                 desc: str,
                 author: str,
                 licence: str,
                 core: Core):
        self.id = id
        self.name = name
        self.desc = desc
        self.author = author
        self.licence = licence
        self.core = core
        self.function_meta = {}
        self.results = []

    def run(self, function: str, arguments: []) -> RunResult:
        """Run a remote function and return a :Result

        :param function: name of the function
        :param arguments: function arguments | empty list or None for no args
        :return: :RunResult
        :raises :RemoteRunError if run call failed
        """
        run_call = ApiRun(self.id, function, arguments)
        result = self.core.send_run(run_call)

        result.called_by_id = self.id
        result.called_function = function
        result.call_arguments = arguments
        self.results.append(result)

        return result
