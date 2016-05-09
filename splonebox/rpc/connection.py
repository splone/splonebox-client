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

import threading
import logging
import socket

from splonebox.rpc.crypto import Crypto
from splonebox.rpc.crypto import InvalidPacketException, \
    PacketTooShortException


class Connection:
    def __init__(self):
        self._buffer_size = pow(1024, 2)  # This is defined my msgpack
        self._ip = None
        self._port = None
        self._listen_thread = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._disconnected = threading.Event()
        self._disconnected.set()
        self.crypto_context = Crypto.by_path()

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

        self._ip = socket.gethostbyname(hostname)
        self._port = port

        logging.debug("Connecting to host: " + hostname + ":" + port.__str__())
        self._socket.connect((self._ip, self._port))
        logging.debug("Connected to: " + self._ip + ":" + port.__str__())

        logging.debug("Preparing encryption..")
        self._init_crypto()
        logging.debug("Encryption initialized!")

        self._disconnected.clear()
        if listen:
            self.listen(msg_callback, new_thread=listen_on_new_thread)

    def _init_crypto(self):
        """
        Executes the crypto handshake w/ server. Raises errors in
        case of failure.
        """

        try:
            logging.debug("Sending hello packet...")
            hellopacket = self.crypto_context.crypto_hello()
            self._socket.sendall(hellopacket)

            logging.debug("Receiving cookie packet..")
            len_cookie_packet = 168
            cookiepacket = self._socket.recv(len_cookie_packet)

            logging.debug("Sending initiate packet..")
            initiatepacket = self.crypto_context.crypto_initiate(cookiepacket)
            self._socket.sendall(initiatepacket)

        except InvalidPacketException as e:
            logging.error("Crypto handshake failed {s}".format(str(e)))
            raise

    def listen(self, msg_callback, new_thread):
        """ Wrapper for the _listen function

        (mostly to make tests easier to implement,
        could be useful in the future as well)

        :param new_thread: Should we listen in a new thread?
        :param msg_callback: This function gets called on incoming messages.
        It has one argument of type bytes
        """
        if new_thread:
            self._listen_thread = threading.Thread(target=self._listen,
                                                   args=(msg_callback, ))
            self._listen_thread.start()
            logging.debug("Start listening..")
        else:
            logging.debug("Start listening..")
            self._listen(msg_callback)

    def disconnect(self):
        """Closes the connection"""
        self._disconnected.set()
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        if self._listen_thread is not None:
            self._listen_thread.join()

    def send_message(self, msg: bytes):
        """Sends given message to server if connected

        :param msg: Message to be sent
        """
        if self._disconnected.is_set():
            raise BrokenPipeError("Connection has been closed")

        self.crypto_context.crypto_established.wait()

        boxed = self.crypto_context.crypto_write(msg)
        self._socket.sendall(boxed)

    def _listen(self, msg_callback):
        """Listens for incoming messages.
        :param msg_callback callback function with one argument (:Message)
        """
        recv_buffer = b''

        while not self._disconnected.is_set():
            try:
                data = self._socket.recv(self._buffer_size)

                if data == b'':
                    self._disconnected.set()
                    logging.warning("Connection was closed by the server!")
                    break
            except:
                if not self._disconnected.is_set():
                    self._disconnected.set()
                    raise
                return

            recv_buffer += data

            try:
                msg_length = self.crypto_context.crypto_verify_length(recv_buffer)
                while (msg_length <= len(recv_buffer) and
                       len(recv_buffer) > 0):
                    plain = self.crypto_context.crypto_read(
                        recv_buffer[:msg_length])
                    msg_callback(plain)

                    recv_buffer = recv_buffer[msg_length:]
            except PacketTooShortException:
                continue
            except InvalidPacketException as e:
                logging.warning(e)
                recv_buffer = b''
