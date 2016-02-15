import logging
import socket
from threading import Thread
from multiprocessing import Lock


class Connection:
    def __init__(self):
        self._buffer_size = pow(1024, 2)  # This is defined my msgpack
        self._ip = None
        self._port = None
        self._listen_thread = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connected = False
        self.is_listening = Lock()

    def connect(self,
                hostname: str,
                port: int,
                msg_callback,
                listen=True,
                listen_on_new_thread=True):
        """Connect to given host

        :param msg_callback: This function gets called on incoming messages.
                             It has one argument of type Message
        :param hostname: hostname
        :param port: port
        :param listen: should we listen for incoming messages?
        :param listen_on_new_thread: should we listen in a new thread?

        :raises: :ConnectionRefusedError if socket is unable to connect
        :raises: socket.gaierror if Host unknown
        :raises: :ConnectionError if hostname or port are invalid types
        """
        if not isinstance(hostname, str):
            raise ConnectionError("Hostname has to be string")

        self._ip = socket.gethostbyname(hostname)

        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ConnectionError("Port has to be an unsigned 16bit integer")

        self._port = port
        logging.info("Connecting to host: " + hostname + ":" + port.__str__())
        self._socket.connect((self._ip, self._port))
        logging.info("Connected to: " + self._ip + ":" + port.__str__())

        self._connected = True

        if listen:
            self.listen(msg_callback, new_thread=listen_on_new_thread)

    def listen(self, msg_callback, new_thread=True):
        """ Wrapper for the _listen function

        (mostly to make tests easier to implement,
        could be useful in the future as well)

        :param new_thread: Should we listen in a new thread?
        :param msg_callback: This function gets called on incoming messages.
        It has one argument of type Message
        """
        if new_thread:
            self._listen_thread = Thread(target=self._listen,
                                         args=(msg_callback, ))
            self._listen_thread.start()
            logging.info("Startet listening..")
        else:
            logging.info("Startet listening..")
            self._listen(msg_callback)

    def disconnect(self):
        """Closes the connection"""
        self._connected = False
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self._listen_thread.join()

    def send_message(self, msg: bytes):
        """Sends given message to server if connected

        :param msg: Message to be sent
        :raises: BrokenPipeError if something is wrong with the connection
        """
        if not self._connected:
            raise BrokenPipeError("Connection has been closed")

        totalsent = 0
        while totalsent < len(msg):
            try:
                sent = self._socket.send(msg[totalsent:])
                if sent == 0:
                    raise BrokenPipeError()
            except (OSError, BrokenPipeError):
                raise BrokenPipeError("Connection has been closed")

            totalsent = totalsent + sent

    def _listen(self, msg_callback):
        """Listens for incoming messages.
        :param msg_callback callback function with one argument (:Message)
        :raises: ConnectionError if connection is unexpectedly terminated
        """
        self.is_listening.acquire(True)
        while self._connected:
            try:
                data = self._socket.recv(self._buffer_size)
                if data == b'':
                    raise BrokenPipeError()
            except (BrokenPipeError, OSError):
                self._connected = False
                self.is_listening.release()
                if self._connected:
                    logging.error("Connection was closed by server!")
                    raise  # only raise on unintentional disconnect
                return

            # let the callback handle the received data
            msg_callback(data)

        self.is_listening.release()  # Tell everyone we are done

    def is_connected(self) -> bool:
        """
        :return: True if connected, False if not
        """
        return self._connected
