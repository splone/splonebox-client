import unittest
import libnacl
import struct

from splonebox.rpc.crypto import Crypto


class CryptoTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.serverlongtermpk, cls.serverlongtermsk = libnacl.\
            crypto_box_keypair()
        cls.servershorttermpk, cls.servershorttermsk = libnacl.\
            crypto_box_keypair()

        cls.crypt = Crypto.by_path()

        cls.crypt.serverlongtermpk = cls.serverlongtermpk

    def test_crypto_init_functional(self):

        #  generate hello packet
        data = self.crypt.crypto_hello()

        #  extract key and generate cookie response
        extracted_key, = struct.unpack("<32s", data[8:40])

        identifier = struct.pack("<8s", b"rZQTd2nC")
        nonce = libnacl.randombytes(16)
        nonce_expanded = struct.pack("<8s16s", b"splonePK", nonce)

        cookie = libnacl.randombytes(96)
        payload = b''.join([self.servershorttermpk, cookie])
        box = libnacl.crypto_box(payload, nonce_expanded,
                                 extracted_key,
                                 self.serverlongtermsk)

        data = b''.join([identifier, nonce, box])

        # generate initiate-packet from cookiepacket
        self.crypt.crypto_initiate(data)

        # test if the crypto is able to decrypt a server message
        identifier = struct.pack("<8s", b"rZQTd2nM")

        server_nonce = self.crypt.crypto_random_mod(281474976710656)
        server_nonce += 0 if server_nonce % 2 == 0 else 1

        nonce_expanded = struct.pack("<16sQ", b"splonebox-server",
                                     server_nonce)

        payload = libnacl.randombytes(96)
        length = struct.pack("<Q", 56 + len(payload))

        length_boxed = libnacl.crypto_box(length, nonce_expanded,
                                          extracted_key,
                                          self.servershorttermsk)

        server_nonce += 2
        nonce_expanded = struct.pack("<16sQ", b"splonebox-server",
                                     server_nonce)

        box = libnacl.crypto_box(payload, nonce_expanded,
                                 extracted_key,
                                 self.servershorttermsk)

        msg = b"".join([identifier, struct.pack("<Q", server_nonce - 2),
                        length_boxed, box])

        extr = self.crypt.crypto_read(msg)
        self.assertEqual(extr, payload)

        # test if the crypto is able to encrypt a message properly
        payload = libnacl.randombytes(96)
        data = self.crypt.crypto_write(payload)

        identifier, = struct.unpack("<8s", data[:8])
        nonce, = struct.unpack("<Q", data[8:16])
        nonceexpanded = struct.pack("<16sQ", b"splonebox-client", nonce)
        length = libnacl.crypto_box_open(data[16:40], nonceexpanded,
                                         self.crypt.clientshorttermpk,
                                         self.servershorttermsk)
        nonceexpanded = struct.pack("<16sQ", b"splonebox-client", nonce+2)
        plaintext = libnacl.crypto_box_open(data[40:],
                                            nonceexpanded,
                                            self.crypt.clientshorttermpk,
                                            self.servershorttermsk)
        self.assertEqual(plaintext, payload)
