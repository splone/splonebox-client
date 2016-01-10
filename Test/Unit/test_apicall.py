import unittest
from Splonecli.Api.apicall import InvalidApiCallError, ApiRun, ApiRegister
from Splonecli.Rpc.message import MRequest, InvalidMessageError


def collect_tests(suite: unittest.TestSuite):
	suite.addTest(ApiCallTest("test_apiregister"))
	suite.addTest(ApiCallTest("test_apirun"))
	suite.addTest(ApiCallTest("test_from_msgpack_request"))
	pass


class ApiCallTest(unittest.TestCase):
	def test_from_msgpack_request(self):
		msg = MRequest()
		msg.function = "run"

		msg.arguments = [[b'apikey'], b'fun', []]
		call = ApiRun.from_msgpack_request(msg)
		self.assertEqual(call.__class__, ApiRun("a", "b", []).__class__)
		self.assertEqual(call.msg.arguments[0][0],
						 msg.arguments[0][0].decode('ascii'))
		self.assertEqual(call.msg.arguments[1],
						 msg.arguments[1].decode('ascii'))

		msg.function = None
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

		msg.arguments = [[1], b'fun', []]
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

		msg.arguments = [[b'key'], 1, []]
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

		msg.arguments = ["hi", 0, []]
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

		msg.arguments = [[b"k"], 0, "hi"]
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

		msg.arguments = [[b"k", 1], 0, []]
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

		msg.arguments = [[b"k", 1], 0, []]
		with self.assertRaises(InvalidMessageError):
			ApiRun.from_msgpack_request(msg)

	def test_apiregister(self):
		metadata = ["api_key", "plugin_name", "description", "MIT", "Guy"]
		functions = [["foo", "do_foo", [3, -1, 2.0, "", False, b'']]]
		call = ApiRegister(metadata, functions)

		self.assertEqual(call.msg.function, "register")
		self.assertEqual(call.msg.arguments, [metadata, functions])

		for i in range(5):
			with self.assertRaises(InvalidApiCallError):
				temp = metadata.copy()
				temp[i] = None
				ApiRegister(temp, functions)

		invalid = [0.0, 1, -1, b'hi', True]
		for i in range(5):
			with self.assertRaises(InvalidApiCallError):
				temp = metadata.copy()
				temp[i] = invalid[i]
				ApiRegister(temp, functions)

		with self.assertRaises(InvalidApiCallError):
			ApiRegister(None, functions)

		with self.assertRaises(InvalidApiCallError):
			ApiRegister(metadata, None)

		invalid = [1.2, 800, -92, b'hi', True, "something"]
		for inv in invalid:
			with self.assertRaises(InvalidApiCallError):
				ApiRegister(metadata, [["a", "b", [inv]]])

		with self.assertRaises(InvalidApiCallError):
			ApiRegister(metadata, ["bla"])

		with self.assertRaises(InvalidApiCallError):
			ApiRegister(metadata, [None])

		pass

	def test_apirun(self):
		api_key = "key"
		function_name = "name"
		args = [0]

		call = ApiRun(api_key, function_name, args)
		self.assertEqual(call.msg.function, "run")
		self.assertEqual(call.get_api_key(), api_key)
		self.assertEqual(call.get_method_name(), function_name)
		self.assertEqual(call.get_method_args(), args)
		self.assertEqual(call.msg.arguments, [[api_key], function_name, args])

		with self.assertRaises(InvalidApiCallError):
			ApiRun(2, function_name, args)

		with self.assertRaises(InvalidApiCallError):
			ApiRun(api_key, 2, args)

		with self.assertRaises(InvalidApiCallError):
			ApiRun(api_key, function_name, [None])

		with self.assertRaises(InvalidApiCallError):
			ApiRun(api_key, function_name, [[]])

		with self.assertRaises(InvalidApiCallError):
			ApiRun(api_key, function_name, [object()])
