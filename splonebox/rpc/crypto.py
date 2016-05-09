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

from Crypto.Cipher import AES
import libnacl.utils
import libnacl
import threading
import logging
import struct
import os

from splonebox.os.filesystem import open_lock
from splonebox.os.filesystem import save_sync

counterlow = 0
counterhigh = 0
keyloaded = False
noncekey = 0


class InvalidPacketException(Exception):
    pass


class PacketTooShortException(InvalidPacketException):
    pass


def load_key(path: str) -> bytes:
    """Load a key from a file
    :raises :TypeError if path is not a string
    :raises :IOError if file cannot be opened
    """
    if not isinstance(path, str):
        raise TypeError()

    with open(path, 'rb') as f:
        key = f.read()

    return key


def crypto_block(data: bytes, k: bytes) -> bytes:
    iv = libnacl.randombytes(AES.block_size)
    cipher = AES.new(k, AES.MODE_CBC, iv)
    return cipher.encrypt(data)


class Crypto:
    """Crypto stack implementation of splone crypto protocol
    https://github.com/splone/splonebox-core/wiki/Crypto
    """

    def __init__(self, clientlongtermpk, clientlongtermsk,
                 serverlongtermpk):
        """
        Constructs a crypto object.

        clientlongtermpk -- client's long term public key
        clientlongtermsk -- client's long term secret key
        serverlongtermpk -- server's long term public key

        """

        self.serverlongtermpk = serverlongtermpk
        self.clientlongtermpk = clientlongtermpk
        self.clientlongtermsk = clientlongtermsk

        self.clientshorttermsk = None
        self.clientshorttermpk = None
        self.servershorttermpk = None

        self.nonce = self.crypto_random_mod(281474976710656)
        self.nonce += 1 if self.nonce % 2 == 0 else 0
        self.last_received_nonce = 0

        self.crypto_established = threading.Event()

    @classmethod
    def by_path(cls,
                clientlongtermpk='.keys/client-long-term.pub',
                clientlongtermsk='.keys/client-long-term',
                serverlongtermpk='.keys/server-long-term.pub'):
        """
        Constructor to create a Crypto class by passing path to keys
        instead of passing keys directly.

        clientlongtermpk -- path to client's long term public key
        clientlongtermsk -- path to client's long term secret key
        serverlongtermpk -- path to server's long term public key

        """
        clientlongtermpk = load_key(clientlongtermpk)
        clientlongtermsk = load_key(clientlongtermsk)
        serverlongtermpk = load_key(serverlongtermpk)
        return cls(clientlongtermpk, clientlongtermsk, serverlongtermpk)

    @staticmethod
    def safenonce():
        """
        This method generates a crypto nonce, returns it as well as
        stores it on disk. Crypto using those long term keys requires
        the nonce to be unique even if the process is restarted. So we
        need to keep track of it even after a process reboot.

        The 24 byte nonce conists of
        8 bytes: 'splonePV' prefix
        8 bytes: counter
        8 bytes: random bytes

        """
        global keyloaded
        global counterlow
        global counterhigh
        global noncekey

        fdlock = open_lock(".keys/lock")

        try:

            if not keyloaded:

                noncekey = load_key(".keys/noncekey")
                keyloaded = True

            if counterlow >= counterhigh:

                noncecounter = load_key(".keys/noncecounter")
                counterlow, = struct.unpack("<Q", noncecounter)
                counterhigh = counterlow + 1

                data = struct.pack("<Q", counterhigh)
                save_sync(".keys/noncecounter", data)

            data = struct.pack("<Q8s", counterlow, libnacl.randombytes(8))
            counterlow += 1

            nonce = crypto_block(data, noncekey)

        except:
            logging.error("Failed to generated safe nonce!")
            raise

        finally:
            os.close(fdlock)

        return nonce

    def crypto_verify_length(self, data: bytes) -> bytes:
        """
        Extracts and verifies the length bytes of a server message
        packet. Raises an InvalidPacketException in case of invalid
        length. It verifies message identifier, too.

        data -- payload of a server message packet
        returns -- packet length

        """
        if not len(data) >= 40:
            raise PacketTooShortException("Message to short")

        identifier, = struct.unpack("<8s", data[:8])

        if identifier.decode('ascii') != "rZQTd2nM":
            raise InvalidPacketException("Received identifier is bad")

        nonce, = struct.unpack("<Q", data[8:16])
        nonceexpanded = struct.pack("<16sQ", b"splonebox-server", nonce)

        try:
            data = libnacl.crypto_box_open(data[16:40], nonceexpanded,
                                           self.servershorttermpk,
                                           self.clientshorttermsk)
            length, = struct.unpack("<Q", data)

        except (ValueError, libnacl.CryptError) as e:
            logging.error(e)
            raise InvalidPacketException(
                    "Failed to verify length of message packet!")

        return length

    def crypto_write(self, data: bytes) -> bytes:
        """Create a client message packet consisting of:
        * 8 bytes: the ASCII bytes "oqQN2kaM"
        * 8 bytes: a client-selected compressed nonce in little-endian form.
                   This compressed nonce is implicitly prefixed by
                   "splonebox-server" to form a 24-byte nonce.
        * 24 bytes: a cryptographic box encrypted and authenticated to the
                    client's short-term public key C' from the server's short-term public
                    key S' using this 24-byte nonce. The M-byte plaintext inside the box has
                    the following contents:
            * 8 bytes: length
        * n bytes: a cryptographic box encrypted and authenticated to the
                    client's short-term public key C' from the server's
                    short-term public key S' using this 24-byte nonce. The
                    plaintext inside the box has the following contents:
            * m bytes: data

        :return: client message packet
        :raises: :CryptError on failure
        """
        self.crypto_nonce_update()
        message_nonce = struct.pack("<Q", self.nonce)

        length = struct.pack("<Q", 56 + len(data))
        length_nonce = struct.pack("<16sQ", b"splonebox-client", self.nonce)

        length_boxed = libnacl.crypto_box(length, length_nonce,
                                          self.servershorttermpk,
                                          self.clientshorttermsk)

        self.crypto_nonce_update()
        identifier = struct.pack("<8s", b"oqQN2kaM")
        data_nonce = struct.pack("<16sQ", b"splonebox-client", self.nonce)
        box = libnacl.crypto_box(data, data_nonce, self.servershorttermpk,
                                 self.clientshorttermsk)

        return b"".join([identifier, message_nonce, length_boxed, box])

    def crypto_hello(self) -> bytes:
        """Create a client tunnel packet consisting of:
        * 8 bytes: the ASCII bytes "oqQN2kaH"
        * 32 bytes: client's short-term public key C'
        * 64 bytes: all zero
        * 8 bytes: a client-selected compressed nonce in little-endian
                   form. This compressed nonce is implicitly prefixed by
                   "splonebox-client" to form a 24-byte nonce
        * 80 bytes: a cryptographic box encrypted and authenticated to the
                    server's long-term public key S from the client's short-term
                    public key C' using this 24-byte nonce. The 64-byte
                    plaintext inside the box has the following contents:
            * 64 bytes: all zero

        :return: client hello packet
        """
        self.crypto_nonce_update()

        identifier = struct.pack("<8s", b"oqQN2kaH")
        nonce = struct.pack("<16sQ", b"splonebox-client-H", self.nonce)
        zeros = bytearray(64)

        self.clientshorttermpk, \
            self.clientshorttermsk = libnacl.crypto_box_keypair()
        box = libnacl.crypto_box(zeros, nonce, self.serverlongtermpk,
                                 self.clientshorttermsk)

        nonce = struct.pack("<Q", self.nonce)

        return b"".join([identifier, self.clientshorttermpk, zeros, nonce, box])

    def _verify_cookiepacket(self, cookiepacket) -> bytes:
        """
        Validates the cookie packet and extracts the cookie. In case
        of being invalid the function raises a InvalidPacketException.

        cookiepacket -- actual cookie packet sent by server
        result -- returns cookie extracted

        """
        if not len(cookiepacket) == 168:
            raise InvalidPacketException("Cookie packet has invalid length.")

        identifier, = struct.unpack("<8s", cookiepacket[:8])
        if identifier.decode('ascii') != "rZQTd2nC":
            raise InvalidPacketException("Received identifier is bad")

        nonce, = struct.unpack("<16s", cookiepacket[8:24])

        # TODO: verify nonce increased from previously received nonces

        nonceexpanded = struct.pack("<8s16s", b"splonePK", nonce)

        try:
            payload = libnacl.crypto_box_open(cookiepacket[24:], nonceexpanded,
                                              self.serverlongtermpk,
                                              self.clientshorttermsk)
        except (ValueError, libnacl.CryptError) as e:
            logging.error(e)
            raise InvalidPacketException("Failed to open cookie packet box!")

        self.servershorttermpk, = struct.unpack("<32s", payload[:32])
        cookie, = struct.unpack("<96s", payload[32:128])
        return cookie

    def crypto_initiate(self, cookiepacket) -> bytes:
        """ Validate the cookie packet and create the corresponding
        initate packet consisting of:

        * 8 bytes: the ASCII bytes "oqQN2kaI".
        * 96 bytes: the server's cookie.
        * 8 bytes: a client-selected compressed nonce in little-endian form.
                  This compressed nonce is implicitly prefixed by
                  "splonebox-client" to form a 24-byte nonce.
        * 144 bytes: a cryptographic box encrypted and authenticated to the
                    server's short-term public key S' from the client's
                    short-term public key C' using this 24-byte nonce. The
                    (96+M)-byte plaintext inside the box has the following
                    contents:
          * 32 bytes: the client's long-term public key C.
          * 16 bytes: a client-selected compressed nonce in little-endian
                      form. This compressed nonce is implicitly prefixed by
                      "splonePV" to form a 24-byte nonce.
          * 80 bytes: a cryptographic box encrypted and authenticated to the
                      server's long-term public key S from the client's
                      long-term public key C using this 24-byte nonce. The
                      32-byte plaintext inside the box has the following
                      contents:
              * 32 bytes: the client's short-term public key C'.
              * 32 bytes: server's short term public key S'

        cookiepacket -- the cookie packet sent by server

        :return: client initiate packet
        """
        cookie = self._verify_cookiepacket(cookiepacket)
        vouch_payload = b"".join([self.clientshorttermpk,
                                  self.servershorttermpk])
        vouch_nonce = self.safenonce()
        vouch_nonce_expanded = struct.pack("<8s16s", b"splonePV", vouch_nonce)

        vouch_box = libnacl.crypto_box(vouch_payload,
                                       vouch_nonce_expanded,
                                       self.serverlongtermpk,
                                       self.clientlongtermsk)

        payload = b"".join([self.clientlongtermpk, vouch_nonce,
                            vouch_box])

        self.crypto_nonce_update()

        payload_nonce = struct.pack("<16sQ", b"splonebox-client", self.nonce)
        payload_box = libnacl.crypto_box(payload, payload_nonce,
                                         self.servershorttermpk,
                                         self.clientshorttermsk)

        identifier = struct.pack("<8s", b"oqQN2kaI")

        nonce = struct.pack("<Q", self.nonce)
        initiatepacket = b"".join([identifier, cookie, nonce,
                                   payload_box])

        self.crypto_established.set()
        return initiatepacket

    def crypto_read(self, data: bytes) -> bytes:
        """Read a server message packet consisting of:
        * 8 bytes: the ASCII bytes "rZQTd2nM"
        * 8 bytes: packet length
        * 8 bytes: a server-selected compressed nonce in little-endian form.
                   This compressed nonce is implicitly prefixed by
                   "splonebox-server" to form a 24-byte nonce.
        * n bytes: a cryptographic box encrypted and authenticated to the
                    client's short-term public key C' from the server's
                    short-term public key S' using this 24-byte nonce. The
                    plaintext inside the box has the following contents:
            * m bytes: data

        :return: server message packet
        :raises: InvalidPacketException in case of error
        """
        length = self.crypto_verify_length(data)

        nonce, = struct.unpack("<Q", data[8:16])
        self._verify_nonce(nonce)

        nonceexpanded = struct.pack("<16sQ", b"splonebox-server", nonce + 2)
        try:
            plain = libnacl.crypto_box_open(data[40:length], nonceexpanded,
                                            self.servershorttermpk,
                                            self.clientshorttermsk)
        except (ValueError, libnacl.CryptError) as e:
            logging.error(e)
            raise InvalidPacketException("Failed to unbox message!")

        self.last_received_nonce = nonce

        return plain

    @staticmethod
    def crypto_random_mod(number: int) -> int:
        """Generate a random random integer"""
        result = 0

        if number <= 1:
            return 0

        random = libnacl.randombytes(32)

        for j in range(0, 32):
            result = (result * 256 + random[j]) % number

        return result

    def crypto_nonce_update(self):
        """Increment the nonce"""
        self.nonce += 2

    def _verify_nonce(self, nonce):
        """ Raises an InvalidPacketException if nonce is invalid """
        if (nonce <= self.last_received_nonce or nonce % 2 == 1):
            raise InvalidPacketException("Invalid Nonce!")
