from functools import cached_property

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from stakewise_cli.utils import bytes_to_str, str_to_bytes

CIPHER_KEY_LENGTH = 32


class Decoder:
    def __init__(self, decryption_key: str):
        self.decryption_key = decryption_key

    def decrypt(self, data: str, nonce: str) -> str:
        cipher = self._restore_cipher(nonce=nonce)
        private_key = cipher.decrypt(str_to_bytes(data))
        return private_key.decode("ascii")

    def _restore_cipher(self, nonce: str) -> AES.MODE_EAX:
        cipher = AES.new(
            str_to_bytes(self.decryption_key), AES.MODE_EAX, nonce=str_to_bytes(nonce)
        )
        return cipher


class Encoder:
    @cached_property
    def cipher_key(self) -> bytes:
        return get_random_bytes(CIPHER_KEY_LENGTH)

    @cached_property
    def cipher_key_str(self) -> str:
        return bytes_to_str(self.cipher_key)

    def encrypt(self, data: str):
        cipher = self._generate_cipher()
        encrypted_data = cipher.encrypt(bytes(data, "ascii"))
        return encrypted_data, cipher.nonce

    def _generate_cipher(self) -> AES.MODE_EAX:
        return AES.new(self.cipher_key, AES.MODE_EAX)
