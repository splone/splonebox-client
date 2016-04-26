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
import unittest

from test.unit import test_apicall
from test.unit import test_remotefunction
from test.unit import test_plugin
from test.unit import test_result
from test.unit import test_message
from test.unit import test_msgpackrpc
from test.unit import test_connection
from test.unit import test_crypto

from test.functional import test_remote_calls
from test.functional import test_local_call
from test.functional import test_complete_call

# create test suite
suite = unittest.TestSuite()
loader = unittest.defaultTestLoader

suite.addTests([
    loader.loadTestsFromModule(test_apicall),
    loader.loadTestsFromModule(test_remotefunction),
    loader.loadTestsFromModule(test_plugin),
    loader.loadTestsFromModule(test_result),
    loader.loadTestsFromModule(test_message),
    loader.loadTestsFromModule(test_msgpackrpc),
    loader.loadTestsFromModule(test_connection),
    loader.loadTestsFromModule(test_crypto),
    loader.loadTestsFromModule(test_remote_calls),
    loader.loadTestsFromModule(test_local_call),
    loader.loadTestsFromModule(test_complete_call),
])

# functional
# Deactivate warnings and Logs
logging.basicConfig(level=logging.CRITICAL)

# Activate Logs
#logging.basicConfig(level=logging.INFO)

# run all tests
unittest.TextTestRunner(verbosity=3).run(suite)
