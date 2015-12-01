import unittest


from Splonecli.Connection.message import MRequest, Message, MResponse, MNotify


class MessageTest(unittest.TestCase):
    def test_MRequest(self):
        msg_request = MRequest()
        msg_request.method = b'run'
        msg_request.body = [b'hi']

        packed = msg_request.pack()
        unpacked = Message.unpack(packed)

        self.assertTrue(msg_request == unpacked)

        msg_request.body = None
        self.assertIsNone(msg_request.pack())

    def test_MResponse(self):
        msg_response = MResponse()
        msg_response.error = b'err'
        msg_response.body = [b'hi']

        packed = msg_response.pack()
        unpacked = Message.unpack(packed)

        self.assertTrue(msg_response == unpacked)

        msg_response.body = None
        self.assertIsNone(msg_response.pack())

    def test_MNotify(self):
        msg_notify = MNotify()
        msg_notify.error = b'err'
        msg_notify.body = [b'hi']

        packed = msg_notify.pack()
        unpacked = Message.unpack(packed)

        self.assertTrue(msg_notify == unpacked)

        msg_notify.body = None
        self.assertIsNone(msg_notify.pack())




if __name__ == '__main__':
    unittest.main()
