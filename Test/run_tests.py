import logging
import unittest

from Test.Functional import test_remote_calls, test_local_call, \
 test_complete_call, test_socket_error_handling
from Test.Unit import test_connection, test_message, \
 test_msgpackrpc, test_plugin, test_remotefunction, test_result, \
 test_apicall

# create test suite
suite = unittest.TestSuite()

# collect all tests

# Api
test_apicall.collect_tests(suite)
test_remotefunction.collect_tests(suite)
test_plugin.collect_tests(suite)
test_result.collect_tests(suite)
# Rpc
test_message.collect_tests(suite)
test_msgpackrpc.collect_tests(suite)
test_connection.collect_tests(suite)
# Functional
test_remote_calls.collect_tests(suite)
test_local_call.collect_tests(suite)
test_complete_call.collect_tests(suite)
#test_socket_error_handling.collect_tests(suite)

# Deactivate warnings and Logs
logging.basicConfig(level=logging.ERROR)

# Activate Logs
# logging.basicConfig(level=logging.INFO)

# run all tests
unittest.TextTestRunner(verbosity=3).run(suite)
