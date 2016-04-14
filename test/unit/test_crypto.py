from random import randint
import unittest.mock as mock
import unittest
import libnacl
import struct
import os

from splonecli.rpc.crypto import Crypto
from splonecli.rpc.crypto import InvalidPacketException


def collect_tests(suite: unittest.TestSuite):
    suite.addTest(CryptoTest("test_crypto_random_mod"))
    suite.addTest(CryptoTest("test_load_key"))
    suite.addTest(CryptoTest("test_crypto_tunnel"))
    suite.addTest(CryptoTest("test_crypto_nonce_update"))
    suite.addTest(CryptoTest("test_crypto_tunnel_read"))
    suite.addTest(CryptoTest("test_crypto_write"))
    suite.addTest(CryptoTest("test_crypto_read"))


class CryptoTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.serverlongtermpk, cls.serverlongtermsk = libnacl.\
            crypto_box_keypair()
        cls.servershorttermpk, cls.servershorttermsk = libnacl.\
            crypto_box_keypair()

        cls.crypt = Crypto.by_path()

        cls.crypt.serverlongtermpk = cls.serverlongtermpk
        cls.crypt.servershorttermpk = cls.servershorttermpk


    def test_010_hello_packet(self):
        """ Verify that the hello packet is properly build. """
        data = self.crypt.crypto_hello()

        identifier, = struct.unpack("<8s", data[:8])
        self.assertEqual(identifier.decode('ascii'), "oqQN2kaH")

        clientshorttermpk, = struct.unpack("<32s", data[8:40])
        self.assertEqual(clientshorttermpk, self.crypt.clientshorttermpk)

        allzero, = struct.unpack("<64s", data[40:104])
        self.assertEqual(allzero, bytearray(64))

        nonce, = struct.unpack("<Q", data[104:112])
        self.assertEqual(nonce, self.crypt.nonce)
        self.assertTrue(nonce % 2 == 1)

        nonceexpanded = struct.pack("<16sQ", b"splonebox-client", nonce)
        clear_msg = libnacl.crypto_box_open(data[112:], nonceexpanded,
            self.crypt.clientshorttermpk, self.serverlongtermsk)
        self.assertEqual(clear_msg, bytearray(64))

    def test_020_crypto_write(self):
        """ Verify whether message packet is properly build. """
        payload = libnacl.randombytes(40)
        data = self.crypt.crypto_write(payload)

        identifier, = struct.unpack("<8s", data[:8])
        self.assertEqual(identifier.decode('ascii'), "oqQN2kaM")

        nonce, = struct.unpack("<Q", data[8:16])
        self.assertEqual(nonce + 2, # add two since nonce is increased
                                    # to boxing the payload (and not
                                    # only the length)
                         self.crypt.nonce)
        self.assertTrue(nonce % 2 == 1)

        nonceexpanded = struct.pack("<16sQ", b"splonebox-client", nonce)
        length = libnacl.crypto_box_open(data[16:40], nonceexpanded,
            self.crypt.clientshorttermpk, self.servershorttermsk)
        self.assertEqual(struct.unpack("Q", length)[0], len(data))

        nonceexpanded = struct.pack("<16sQ", b"splonebox-client", nonce+2)
        plaintext = libnacl.crypto_box_open(data[40:], nonceexpanded,
            self.crypt.clientshorttermpk, self.servershorttermsk)
        self.assertEqual(plaintext, payload)

    def test_030_verify_length(self):
        """ Verify whether length is properly extraced. """
        payload = libnacl.randombytes(40)
        nonce = self.crypt.last_received_nonce + 2

        nonce_length = struct.pack("<16sQ", b"splonebox-server", nonce)

        length = 40 + len(payload)
        packed_length = struct.pack("<Q", length)
        boxed_length = libnacl.crypto_box(packed_length,
            nonce_length, self.crypt.clientshorttermpk, self.servershorttermsk)

        identifier = struct.pack("<8s", b"rZQTd2nM")
        packed_nonce = struct.pack("<Q", nonce)
        data = b''.join([identifier, packed_nonce, boxed_length, payload])

        # good case
        length_extracted = self.crypt.crypto_verify_length(data)
        self.assertEqual(length, length_extracted)

        # message too short to hold proper length information
        self.assertRaises(InvalidPacketException,
                self.crypt.crypto_verify_length, data[:39])

        # message has illegal identifier
        data = b''.join([struct.pack("<8s", b'foobar'), packed_nonce,
            boxed_length, payload])
        self.assertRaises(InvalidPacketException,
                self.crypt.crypto_verify_length, data)

        # length has been altered
        data = b''.join([identifier, packed_nonce, libnacl.randombytes(32),
            payload])
        self.assertRaises(InvalidPacketException,
                self.crypt.crypto_verify_length, data)

    def test_040_verify_cookiepacket(self):
        """ Check whether cookie is properly extraced. """
        identifier = struct.pack("<8s", b"rZQTd2nC")
        nonce = libnacl.randombytes(16)
        nonce_expanded = struct.pack("<8s16s", b"splonePK", nonce)

        cookie = libnacl.randombytes(96)
        payload = b''.join([self.servershorttermpk, cookie])
        box = libnacl.crypto_box(payload, nonce_expanded,
            self.crypt.clientshorttermpk, self.serverlongtermsk)

        # good case
        data = b''.join([identifier, nonce, box])
        cookie_extracted = self.crypt._verify_cookiepacket(data)
        self.assertEqual(cookie, cookie_extracted)

        # too short
        self.assertRaises(InvalidPacketException,
            self.crypt._verify_cookiepacket, data[:167])

        # message has illegal identifier
        data = b''.join([struct.pack("<8s", b'foobar'), nonce, box])
        self.assertRaises(InvalidPacketException,
                self.crypt._verify_cookiepacket, data)

        # manipulated payload
        data = b''.join([identifier, nonce, libnacl.randombytes(len(box))])
        self.assertRaises(InvalidPacketException,
                self.crypt._verify_cookiepacket, data)

    def test_050_verify_nonce(self):
        """ Verify nonce verification. """
        self.assertIsNone(
            self.crypt._verify_nonce(self.crypt.last_received_nonce + 2))

        self.assertRaises(InvalidPacketException,
            self.crypt._verify_nonce, self.crypt.last_received_nonce + 1)

        self.assertRaises(InvalidPacketException,
            self.crypt._verify_nonce, self.crypt.last_received_nonce)

        self.assertRaises(InvalidPacketException,
            self.crypt._verify_nonce, self.crypt.last_received_nonce - 1)

        self.assertRaises(InvalidPacketException,
            self.crypt._verify_nonce, self.crypt.last_received_nonce - 2)

    def test_060_initiate_packet(self):
        """ Verify that the correct initiate packet is build. """
        cookie = libnacl.randombytes(96)
        self.crypt._verify_cookiepacket = mock.Mock(return_value=cookie)
        data = self.crypt.crypto_initiate(b'dummy')

        identifier = struct.unpack("<8s", data[:8])[0]
        self.assertEqual(b"oqQN2kaI", identifier)

        cookie_extracted = struct.unpack("<96s", data[8:104])[0]
        self.assertEqual(cookie_extracted, cookie)



        # invalid message length

        # invalid identifier

        # invalid nonce

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
        nonce = self.crypt.nonce
        self.crypt.crypto_nonce_update()
        self.assertTrue(nonce % 2 == 1)
        self.assertEqual(nonce + 2, self.crypt.nonce)
