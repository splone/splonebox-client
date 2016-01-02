import socket
from _thread import start_new_thread
from multiprocessing import Lock


class Connection:
    def __init__(self):
        self._buffer_size = pow(1024, 2)  # This is defined my msgpack
        self._ip = None
        self._port = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.is_listening = Lock()

    def connect(self, hostname: str, port: int, msg_callback):
        """
        Connect to given host
        :param msg_callback: This function gets called on incoming messages. It has one argument of type Message
        :param hostname: hostname
        :param port: port

        :raises: ConnectionRefusedError if socket is unable to connect
        :return:
        """
        self._ip = socket.gethostbyname(hostname)
        self._port = port
        try:
            self._socket.connect((self._ip, self._port))
        except:
            raise ConnectionRefusedError("\n Unable to connect to " + self._ip + ":" + self._port.__str__())

        self.connected = True
        start_new_thread(self._listen, (msg_callback,))

    def disconnect(self):
        """
        Closes the socket
        :return:
        """
        self.connected = False
        self._socket.close()

    def send_message(self, msg: bytes):
        """
        :raises: BrokenPipeError
        :param msg:
        :return:
        """
        if self.connected:
            self._socket.send(msg)
        else:
            raise BrokenPipeError()

    def _listen(self, msg_callback):
        """
        Listens for incoming messages.
        :raises: ConnectionError if connection is unexpectedly terminated
        :return:
        """

        self.is_listening.acquire(True)  # Use this to keep Plugin running
        while True and self.connected:
            try:
                data = self._socket.recv(self._buffer_size)
            except socket.error:
                if self.connected:
                    raise ConnectionError("Connection was unexpectedly terminated")

                self.is_listening.release()
                return
            # let the callback handle the received data
            msg_callback(data)

        self.is_listening.release()  # Tell everyone we are done

    def is_connected(self) -> bool:
        """
        :return: True if connected, False if not
        """
        return self.connected
