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
import socket
import struct
from threading import Thread
from multiprocessing import Lock
from multiprocessing import Semaphore
from splonecli.rpc.crypto import Crypto
from splonecli.rpc.crypto import CryptoState


class Connection:
    def __init__(self,
                 serverlongtermpk=None,
                 serverlongtermpk_path='.keys/server-long-term.pub'):
        """
        :param serverlongtermpk: The server's longterm key
        (if set, path is ignored!)
        :param serverlongtermpk_path: path to file containing the
        server's longterm key
        """
        self._buffer_size = pow(1024, 2)  # This is defined my msgpack
        self._recv_buffer = b''
        self._ip = None
        self._port = None
        self._listen_thread = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connected = False
        self.is_listening = Lock()
        self.crypto_context = Crypto(
            serverlongtermpk=serverlongtermpk,
            serverlongtermpk_path=serverlongtermpk_path)
        self.tunnelestablished_sem = Semaphore(value=0)

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

        logging.info("Preparing encryption..")
        tunnelpacket = self.crypto_context.crypto_tunnel()

        try:
            sent = self._socket.send(tunnelpacket)
            if sent == 0:
                logging.info("Encryption could not be initialized!")
                raise BrokenPipeError()
        except (OSError, BrokenPipeError):
            raise BrokenPipeError("Connection has been closed")
        logging.info("Encryption initialized!")

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

        if self.crypto_context.state != CryptoState.ESTABLISHED:
            self.tunnelestablished_sem.acquire()

        boxed = self.crypto_context.crypto_write(msg)

        totalsent = 0
        while totalsent < len(boxed):
            try:
                sent = self._socket.send(boxed[totalsent:])
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
            except (BrokenPipeError, OSError, ConnectionResetError):
                self.is_listening.release()
                if self._connected:
                    logging.warning("Connection was closed by server!")
                    self._connected = False
                    raise  # only raise on unintentional disconnect
                return

            self._recv_buffer += data
            recv_length = len(self._recv_buffer)
            if recv_length > 15:
                msg_length, = struct.unpack("<Q", self._recv_buffer[8:16])

            if self.crypto_context.state == CryptoState.INITIAL:
                if recv_length >= msg_length:
                    self.crypto_context.crypto_tunnel_read(
                        self._recv_buffer[:msg_length])
                    self._recv_buffer = self._recv_buffer[msg_length:]

                    if self.crypto_context.state == CryptoState.ESTABLISHED:
                        self.tunnelestablished_sem.release()
                continue

            while recv_length >= msg_length:
                plain = self.crypto_context.crypto_read(
                    self._recv_buffer[:msg_length])
                self._recv_buffer = self._recv_buffer[msg_length:]
                recv_length = len(self._recv_buffer)
                msg_callback(plain)
                if recv_length > 15:
                    msg_length, = struct.unpack("<Q", self._recv_buffer[8:16])

        self.is_listening.release()

    def is_connected(self) -> bool:
        """
        :return: True if connected, False if not
        """
        return self._connected
