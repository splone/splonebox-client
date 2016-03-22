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

import struct
from enum import Enum
import libnacl
import libnacl.utils


class CryptoState(Enum):
    """CryptoState represents the state of the key agreement protocol"""

    INITIAL = 1
    ESTABLISHED = 2


class Crypto:
    """Crypto stack implementation of splone crypto protocol
    https://github.com/splone/splonebox-core/wiki/Crypto
    """

    def __init__(self, serverlongtermpk=None,
                 serverlongtermpk_path='.keys/server-long-term.pub'):
        self.state = CryptoState.INITIAL

        if(serverlongtermpk is None):
            self.serverlongtermpk = self.load_key(serverlongtermpk_path)
        else:
            self.serverlongtermpk = serverlongtermpk

        self.clientshorttermsk = ""
        self.clientshorttermpk = ""
        self.servershorttermpk = ""
        self.nonce = self.crypto_random_mod(281474976710656)
        self.received_nonce = 0

    def crypto_tunnel(self):
        """Create a client tunnel packet consisting of:
        * 8 bytes: the ASCII bytes "oqQN2kaT"
        * 8 bytes: packet length
        * 8 bytes: a client-selected compressed nonce in little-endian
                   form. This compressed nonce is implicitly prefixed by
                   "splonebox-client" to form a 24-byte nonce
        * 32 bytes: the client's short-term public key C'
        * 80 bytes: a cryptographic box encrypted and authenticated to the
                    server's long-term public key S from the client's short-term
                    public key C' using this 24-byte nonce. The 64-byte
                    plaintext inside the box has the following contents:
            * 64 bytes: all zero

        :return: client tunnel packet
        :raises: :CryptError on failure
        """
        self.crypto_nonce_update()

        identifier = struct.pack("<8s", b"oqQN2kaT")
        length = struct.pack("<Q", 136)
        nonce = struct.pack("<16sQ", b"splonebox-client", self.nonce)
        zeros = bytearray(64)

        self.clientshorttermpk, self.clientshorttermsk = libnacl.crypto_box_keypair()
        box = libnacl.crypto_box(zeros, nonce, self.serverlongtermpk,
                                 self.clientshorttermsk)

        nonce = struct.pack("<Q", self.nonce)

        return b"".join([identifier, length, nonce, self.clientshorttermpk,
                         box])

    def crypto_tunnel_read(self, data: bytes):
        """Read a server tunnel packet consisting of:
        * 8 bytes: the ASCII bytes "rZQTd2nT"
        * 8 bytes: packet length
        * 8 bytes: a server-selected compressed nonce in little-endian form.
                   This compressed nonce is implicitly prefixed by
                   "splonebox-server" to form a 24-byte nonce.
        * 48 bytes: a cryptographic box encrypted and authenticated to the
                    client's short-term public key C' from the server's
                    long-term public key S using this 24-byte nonce. The 32-byte
                    plaintext inside the box has the following contents:
            * 32 bytes: the server's short-term public key S'.

        :return: None
        :raises: :CryptError on failure
        """
        identifier, = struct.unpack("<8s", data[:8])

        if identifier.decode('ascii') != "rZQTd2nT":
            raise ValueError("Received identifier is bad")

        length, = struct.unpack("<Q", data[8:16])
        nonce, = struct.unpack("<Q", data[16:24])
        nonceexpanded = struct.pack("<16sQ", b"splonebox-server", nonce)

        if nonce <= self.received_nonce:
            raise ValueError('Received nonce is bad')

        self.servershorttermpk = libnacl.crypto_box_open(data[24:length],
                                                         nonceexpanded,
                                                         self.serverlongtermpk,
                                                         self.clientshorttermsk)
        self.state = CryptoState.ESTABLISHED

    def crypto_write(self, data: bytes):
        """Create a client message packet consisting of:
        * 8 bytes: the ASCII bytes "oqQN2kaM"
        * 8 bytes: packet length
        * 8 bytes: a client-selected compressed nonce in little-endian form.
                   This compressed nonce is implicitly prefixed by
                   "splonebox-server" to form a 24-byte nonce.
        * n bytes: a cryptographic box encrypted and authenticated to the
                    client's short-term public key C' from the server's
                    short-term public key S' using this 24-byte nonce. The
                    plaintext inside the box has the following contents:
            * m bytes: data

        :return: client message packet
        :raises: :CryptError on failure
        """
        self.crypto_nonce_update()

        identifier = struct.pack("<8s", b"oqQN2kaM")
        nonce = struct.pack("<16sQ", b"splonebox-client", self.nonce)
        box = libnacl.crypto_box(data, nonce, self.servershorttermpk,
                                 self.clientshorttermsk)
        nonce = struct.pack("<Q", self.nonce)
        length = struct.pack("<Q", 24 + len(box))

        return b"".join([identifier, length, nonce, box])

    def crypto_read(self, data: bytes):
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
        :raises: :CryptError on failure
        """
        identifier, = struct.unpack("<8s", data[:8])

        if identifier.decode('ascii') != "rZQTd2nM":
            raise ValueError("Received identifier is bad")

        length, = struct.unpack("<Q", data[8:16])
        nonce, = struct.unpack("<Q", data[16:24])
        nonceexpanded = struct.pack("<16sQ", b"splonebox-server", nonce)

        if nonce <= self.received_nonce:
            raise ValueError('Received nonce is bad')

        plain = libnacl.crypto_box_open(data[24:length],
                                        nonceexpanded,
                                        self.servershorttermpk,
                                        self.clientshorttermsk)

        self.received_nonce = nonce

        return plain

    @staticmethod
    def crypto_random_mod(number: int):
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
        self.nonce += 1

    @staticmethod
    def load_key(path: str):
        """Load a key from a file"""
        stream = open(path, 'rb')

        return stream.read()
