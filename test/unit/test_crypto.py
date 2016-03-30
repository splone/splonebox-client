import unittest
import os
import struct
import libnacl

from splonecli.rpc.crypto import Crypto


def collect_tests(suite: unittest.TestSuite):
    suite.addTest(CryptoTest("test_crypto_random_mod"))
    suite.addTest(CryptoTest("test_load_key"))
    suite.addTest(CryptoTest("test_crypto_tunnel"))
    suite.addTest(CryptoTest("test_crypto_nonce_update"))
    suite.addTest(CryptoTest("test_crypto_tunnel_read"))
    suite.addTest(CryptoTest("test_crypto_write"))
    suite.addTest(CryptoTest("test_crypto_read"))


class CryptoTest(unittest.TestCase):
    def test_crypto_tunnel(self):
        serverpk, serversk = libnacl.crypto_box_keypair()
        crypt = Crypto(serverlongtermpk=serverpk)

        data = crypt.crypto_tunnel()

        identifier, = struct.unpack("<8s", data[:8])
        self.assertEqual(identifier.decode('ascii'), "oqQN2kaT")

        nonce, = struct.unpack("<Q", data[16:24])
        self.assertEqual(nonce, crypt.nonce)
        self.assertTrue(nonce % 2 == 1)

        clientpk = data[24:56]
        self.assertEqual(clientpk, crypt.clientshorttermpk)

        nonceexpanded = struct.pack("<16sQ", b"splonebox-client", nonce)
        length, = struct.unpack("<Q", data[8:16])

        clear_msg = libnacl.crypto_box_open(data[56:length], nonceexpanded,
                                            crypt.clientshorttermpk, serversk)

        self.assertEqual(clear_msg, bytearray(64))

    def test_crypto_tunnel_read(self):
        serverpk, serversk = libnacl.crypto_box_keypair()
        crypt = Crypto(serverlongtermpk=serverpk)
        crypt.clientshorttermpk, \
            crypt.clientshorttermsk = libnacl.crypto_box_keypair()

        identifier = struct.pack("<8s", b"rZQTd2nT")
        length = struct.pack("<Q", 72)
        nonce = 1234
        nonce_bin = struct.pack("<Q", nonce)
        nonce_exp = struct.pack("<16sQ", b"splonebox-server", nonce)
        box = libnacl.crypto_box(serverpk, nonce_exp, crypt.clientshorttermpk,
                                 serversk)
        data = b"".join([identifier, length, nonce_bin, box])

        crypt.crypto_tunnel_read(data)
        self.assertTrue(crypt.crypto_established)

        crypt.servershorttermpk = None

        # invalid message length
        length = struct.pack("<Q", 20)
        data = b"".join([identifier, length, nonce_bin, box])
        with self.assertRaises(libnacl.CryptError):
            crypt.crypto_tunnel_read(data)
        self.assertEqual(crypt.servershorttermpk, None)

        length = struct.pack("<Q", 72)

        # invalid identifier
        identifier = struct.pack("<8s", b"invalid")
        data = b"".join([identifier, length, nonce_bin, box])
        with self.assertRaises(ValueError):
            crypt.crypto_tunnel_read(data)
        self.assertEqual(crypt.servershorttermpk, None)

        identifier = struct.pack("<8s", b"rZQTd2nT")

        # invalid nonce
        nonce = 0
        nonce_bin = struct.pack("<Q", nonce)
        nonce_exp = struct.pack("<16sQ", b"splonebox-server", nonce)
        box = libnacl.crypto_box(serverpk, nonce_exp, crypt.clientshorttermpk,
                                 serversk)
        data = b"".join([identifier, length, nonce_bin, box])
        with self.assertRaises(ValueError):
            crypt.crypto_tunnel_read(data)
        self.assertEqual(crypt.servershorttermpk, None)

    def test_crypto_write(self):
        serverpk, serversk = libnacl.crypto_box_keypair()
        crypt = Crypto(serverlongtermpk=serverpk)
        crypt.clientshorttermpk, \
            crypt.clientshorttermsk = libnacl.crypto_box_keypair()
        crypt.servershorttermpk = serverpk

        data = b'Hello World'
        msg = crypt.crypto_write(data)
        self.assertEqual(struct.unpack("<8s", msg[:8])[0], b"oqQN2kaM")
        self.assertEqual(struct.unpack("<Q", msg[8:16])[0], 51)
        self.assertEqual(struct.unpack("<Q", msg[16:24])[0], crypt.nonce)
        self.assertTrue(crypt.nonce % 2 == 1)
        nonce_exp = struct.pack("<16sQ", b"splonebox-client", crypt.nonce)
        plain = libnacl.crypto_box_open(msg[24:51], nonce_exp,
                                        crypt.clientshorttermpk, serversk)
        self.assertEqual(data, plain)

    def test_crypto_read(self):
        serverpk, serversk = libnacl.crypto_box_keypair()
        crypt = Crypto(serverlongtermpk=serverpk)
        crypt.clientshorttermpk, \
            crypt.clientshorttermsk = libnacl.crypto_box_keypair()
        crypt.servershorttermpk = serverpk

        data = b'Hello World'
        identifier = struct.pack("<8s", b"rZQTd2nM")
        nonce = struct.pack("<16sQ", b"splonebox-server", 1234)
        box = libnacl.crypto_box(data, nonce, crypt.clientshorttermpk,
                                 serversk)
        nonce = struct.pack("<Q", 1234)
        length = struct.pack("<Q", 24 + len(box))

        msg = b"".join([identifier, length, nonce, box])
        content = crypt.crypto_read(msg)
        self.assertEqual(data, content)

        # repeating nonce
        msg = b"".join([identifier, length, nonce, box])
        with self.assertRaises(ValueError):
            crypt.crypto_read(msg)

        # invalid identifier
        crypt.received_nonce = 0
        identifier = struct.pack("<8s", b"invalid")
        msg = b"".join([identifier, length, nonce, box])
        with self.assertRaises(ValueError):
            crypt.crypto_read(msg)
        identifier = struct.pack("<8s", b"rZQTd2nM")

        # invalid length
        crypt.received_nonce = 0
        length = struct.pack("<Q", 1)
        msg = b"".join([identifier, length, nonce, box])
        with self.assertRaises(libnacl.CryptError):
            crypt.crypto_read(msg)
        length = struct.pack("<Q", 24 + len(box))

        # Unmaching nonce
        crypt.received_nonce = 0
        nonce = struct.pack("<Q", 1112)
        msg = b"".join([identifier, length, nonce, box])
        with self.assertRaises(libnacl.CryptError):
            crypt.crypto_read(msg)

    def test_crypto_nonce_update(self):
        key = "somekey"
        crypt = Crypto(serverlongtermpk=key)

        nonce = crypt.nonce
        crypt.crypto_nonce_update()
        self.assertTrue(nonce % 2 == 1)
        self.assertEqual(nonce + 2, crypt.nonce)

    def test_crypto_random_mod(self):
        result = Crypto.crypto_random_mod(100)
        self.assertTrue(result < 100)

        result = Crypto.crypto_random_mod(-1)
        self.assertEqual(result, 0)

        with self.assertRaises(TypeError):
            result = Crypto.crypto_random_mod("Hello")

    def test_load_key(self):
        path = '.splonecli_temp_test_file'
        f = open(path, 'w')
        f.write('something')
        f.close()

        read = Crypto.load_key(path)
        self.assertEqual(read, b'something')
        os.remove(path)

        with self.assertRaises(TypeError):
            Crypto.load_key(2)
