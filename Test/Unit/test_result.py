import unittest

from Api.result import Result, RegisterResult, RemoteError, RunResult


def collect_tests(suite: unittest.TestSuite):
	suite.addTest(ResultTest('test_result'))
	suite.addTest(ResultTest('test_register_result'))
	suite.addTest(ResultTest('test_run_result'))


class ResultTest(unittest.TestCase):
	def test_result(self):
		res = Result()
		self.assertIsNone(res.get_type())
		self.assertIsNone(res._error)
		self.assertFalse(res._event.is_set())

		res.set_error([0, "error"])
		self.assertEqual(res._error, [0, "error"])
		self.assertTrue(res._event.is_set())

		with self.assertRaises(RemoteError):
			res.set_error(1)
		with self.assertRaises(RemoteError):
			res.set_error([0, "err", 5])
		with self.assertRaises(RemoteError):
			res.set_error(["err", 0])
		with self.assertRaises(RemoteError):
			res.set_error([])
		with self.assertRaises(RemoteError):
			res.set_error(None)
		with self.assertRaises(RemoteError):
			res.set_error([0, 0])

	def test_register_result(self):
		res = RegisterResult()

		self.assertEqual(res.get_type(), 0)
		self.assertEqual(res.get_status(), 0)

		res.success()
		self.assertEqual(res.get_status(), 2)
		self.assertIsNone(res.await())

		res = RegisterResult()
		res.set_error([0, "error"])
		self.assertEqual(res.get_status(), -1)
		with self.assertRaises(RemoteError):
			res.await()

	def test_run_result(self):
		res = RunResult()

		self.assertEqual(res.get_type(), 1)
		self.assertEqual(res.get_status(), 0)
		self.assertIsNone(res.get_id())
		self.assertIsNone(res.get_result(blocking=False))
		self.assertFalse(res.has_result())

		res.set_id(42)
		self.assertTrue(res.was_exec())
		self.assertEqual(res.get_id(), 42)
		self.assertFalse(res.has_result())
		self.assertEqual(res.get_status(), 1)

		res.set_result([0])
		self.assertTrue(res.was_exec())
		self.assertTrue(res.has_result())
		self.assertEqual(res.get_status(), 2)
		self.assertEqual(res.get_result(), [0])

		res = RunResult()
		res.set_error([0, "err"])
		with self.assertRaises(RemoteError):
			res.get_result()
		self.assertEqual(res.get_status(), -1)




		pass
