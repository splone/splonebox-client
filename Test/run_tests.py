import ctypes
import logging
import unittest

from Test.Functional import test_remote_calls, test_local_call
from Test.Unit import test_connection, test_dispatcher, test_message, \
    test_msgpackrpc, test_plugin, test_remotefunction
from Test.Unit import test_apicall

# create test suite
suite = unittest.TestSuite()

# collect all tests

# Api
test_apicall.collect_tests(suite)
test_remotefunction.collect_tests(suite)
test_plugin.collect_tests(suite)
# Rpc
test_message.collect_tests(suite)
test_msgpackrpc.collect_tests(suite)
test_connection.collect_tests(suite)
# Functional
test_remote_calls.collect_tests(suite)
test_local_call.collect_tests(suite)

# Deactivate warnings
logging.basicConfig(level=logging.ERROR)

# run all tests
unittest.TextTestRunner(verbosity=3).run(suite)
