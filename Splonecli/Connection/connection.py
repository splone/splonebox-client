import socket
from _thread import start_new_thread

from multiprocessing import Lock

from Splonecli.Connection.dispatcher import Dispatcher
from Splonecli.Connection.message import Message


class Connection:
    def __init__(self):
        self._buffer_size = pow(1024, 2) # This is defined my msgpack See :class: msgpack.Unpacker
        self._ip = None
        self._port = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._dispatcher = None
        self.connected = False
        self.is_listening = Lock()

    def set_dispatcher(self, dispatcher: Dispatcher):
        """
        Set's the dispatcher corresponding to this connection

        :param dispatcher: A :class: `Dispatcher`
        :return:
        """
        assert (self._dispatcher is None and isinstance(dispatcher, Dispatcher))
        self._dispatcher = dispatcher

    def connect(self, name: str, port: int):
        """
        Connect to given host
        :param name: hostname
        :param port: port?
        :return:
        """
        self._ip = socket.gethostbyname(name)
        self._port = port
        self._socket.connect((self._ip, self._port))
        # TODO: Error Handling?
        self.connected = True
        start_new_thread(self._listen, ())
        # TODO: Error Handling?

    def disconnect(self):
        """
        Closes the socket
        :return:
        """
        self.connected = False
        self._socket.close()

    def send_message(self, msg: Message):
        """
        If connected:
        Uses Msgpack to serialize a :class: `Message` and then writes the bytes to the socket
        :param msg:
        :return:
        """
        if self.connected:
            self._socket.send(msg.pack())
        # TODO: some error handling maybe?
        print("Sending this message:\n", msg.pack())

    def _listen(self):
        """
        Listens for incoming messages.
        :return:
        """
        if not self.connected:
            # Todo: Error handling..
            return

        self.is_listening.acquire(True)  # Use this to keep Plugin runing
        while True and self.connected:
            try:
                data = self._socket.recv(self._buffer_size)
            except:
                if(self.connected):
                    print("Ooops something went wrong with your connection")
                self.is_listening.release()
                return

            messages = Message.unpack(data)

            if messages is None:
                # TODO: Maybe some handling? / Is error handling needed?
                continue

            print('Recieved this (these) message(s): \n', list(map(lambda m: m.__str__(), messages)))
            for unpacked in messages:
                if unpacked is None:
                    # TODO: Handle this
                    continue
                elif unpacked.get_type() == 0:
                    # type == 0  => Message is request
                    self._dispatcher.dispatch(unpacked)

        self.is_listening.release() # Tell everyone we are done


