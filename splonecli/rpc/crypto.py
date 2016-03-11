import libnacl
import ctypes
from struct import *
import sys
import binascii
import libnacl.utils

from enum import Enum

class CryptoState(Enum):
	INITIAL = 1
	ESTABLISHED = 2

class Crypto:
	def __init__(self):
		self._state = CryptoState.INITIAL;
		self.serverlongtermpk = self.load_key('.keys/server-long-term.pub')
		self.clientshorttermsk = ""
		self.clientshorttermpk = ""
		self.servershorttermpk = ""
		self.nonce = self.crypto_random_mod(281474976710656)
		self.received_nonce = 0
		self.nacl = libnacl._get_nacl()

	def crypto_tunnel(self):
		self.crypto_nonce_update()

		identifier = pack("<8s", b"oqQN2kaT")
		length = pack("<Q", 136)
		nonce = pack("<16sQ", b"splonebox-client", self.nonce)
		zeros = bytearray(64)

		self.clientshorttermpk, self.clientshorttermsk = libnacl.crypto_box_keypair()
		box = libnacl.crypto_box(zeros, nonce, self.serverlongtermpk, self.clientshorttermsk)

		nonce = pack("<Q", self.nonce)

		return b"".join([identifier, length, nonce, self.clientshorttermpk, box])

	def crypto_tunnel_read(self, data):
		identifier, = unpack("<8s", data[:8])

		if identifier.decode('ascii') != "rZQTd2nT":
			raise ValueError("Received identifier is bad")

		length, = unpack("<Q", data[8:16])
		nonce, = unpack("<Q", data[16:24])
		nonceexpanded = pack("<16sQ", b"splonebox-server", nonce)

		if nonce <= self.received_nonce:
			raise ValueError('Received nonce is bad')

		self.servershorttermpk = libnacl.crypto_box_open(data[24:length], nonceexpanded, self.serverlongtermpk, self.clientshorttermsk)
		self._state = CryptoState.ESTABLISHED


	def crypto_write(self, data):
		self.crypto_nonce_update()

		identifier = pack("<8s", b"oqQN2kaM")
		nonce = pack("<16sQ", b"splonebox-client", self.nonce)
		box = libnacl.crypto_box(data, nonce, self.servershorttermpk, self.clientshorttermsk)
		nonce = pack("<Q", self.nonce)
		length = pack("<Q", 24 + len(box))

		return b"".join([identifier, length, nonce, box])

	def crypto_read(self, data):
		identifier, = unpack("<8s", data[:8])

		if identifier.decode('ascii') != "rZQTd2nM":
			raise ValueError("Received identifier is bad")

		length, = unpack("<Q", data[8:16])
		nonce, = unpack("<Q", data[16:24])
		nonceexpanded = pack("<16sQ", b"splonebox-server", nonce)

		if nonce <= self.received_nonce:
			raise ValueError('Received nonce is bad')

		plain = libnacl.crypto_box_open(data[24:length], nonceexpanded, self.servershorttermpk, self.clientshorttermsk)

		self.received_nonce = nonce

		return plain

	def crypto_random_mod(self, n):
		result = 0

		if n <= 1:
			return 0

		r = libnacl.randombytes(32)

		for j in range(0, 32):
			result = (result * 256 + r[j]) % n

		return result

	def crypto_nonce_update(self):
		self.nonce += 1

	def load_key(self, path):
		stream = open(path, 'rb')

		return stream.read()
