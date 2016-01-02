from Splonecli.Rpc.connection import Connection
from Splonecli.Rpc.dispatcher import Dispatcher, DispatcherError
from Splonecli.Rpc.message import Message, InvalidMessageError, MResponse


class MsgpackRpc:
    def __init__(self):
        self._connection = Connection()
        self._dispatcher = Dispatcher()
        self._response_callbacks = {}
        pass

    def connect(self, host: str, port: int):
        self._connection.connect(host, port, self._message_callback)
        pass

    def send(self, msg: Message, response_callback=None):
        print("sending: \n", msg)
        self._connection.send_message(msg.pack())
        if response_callback is not None:
            self._response_callbacks[msg.get_msgid()] = response_callback
            # if response callback is None we don't expect a response

    def _message_callback(self, data):
        messages = Message.unpack(data)

        for msg in messages:
            try:
                print('Received this message: \n', msg)
                if msg.get_type() == 0:
                    # type == 0  => Message is request
                    self._dispatcher.dispatch(msg)
                elif msg.get_type() == 1:
                    self._handle_response(msg)
                elif msg.get_type() == 2:
                    self._handle_notify(msg)
                else:
                    raise InvalidMessageError("ERROR!: Invalid message Type")
            except InvalidMessageError as e:
                m = MResponse(msg.get_msgid())  # TODO: This might be an invalid msgid! Discuss!
                m.error = [1, e.__str__()]
                self.send(m)
                pass

    def register_function(self, foo, name: str):
        """
        :param name:
        :param foo: a function reference
        :return:
        """
        self._dispatcher.register_function(foo, name)

    def disconnect(self):
        self._connection.disconnect()

    def wait(self):
        self._connection.is_listening.acquire()

    def _handle_response(self, msg: MResponse):
        try:
            self._response_callbacks[msg.get_msgid()](msg)
            self._response_callbacks.pop(msg.get_msgid())
        except:
            if msg.body is None:
                print("Recieved error unrelated to any message!")
                print(msg.error.__str__() + "\n")
            else:
                raise InvalidMessageError("ERROR! The msgid in given response does not match any request!")
        pass

    def _handle_notify(self, msg):
        """
            Notfify Messages are ignored for now
            :param msg:
            :return:
            """
        pass
