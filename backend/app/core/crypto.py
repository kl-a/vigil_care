"""Field encryption (design doc §6.2): AES-256-GCM with keys from the key interface, never in the database.

Every value is sealed with a `context` (e.g. "patient_identity.phone:<patient id>") bound in as associated
data, so a ciphertext copied to another field or Patient won't open. Sealed format:
    version (1 byte) | key id length (1 byte) | key id | nonce (12 bytes) | ciphertext + tag
"""

import os
from typing import Annotated

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, Request

from app.core.seams.keys import Keystore, UnknownKey

VERSION = 1
NONCE_BYTES = 12


class TamperedCiphertext(ValueError):
    """The value won't open: altered, moved to another field or Patient, or sealed with an unknown key."""


class FieldCipher:
    def __init__(self, keystore: Keystore) -> None:
        self._keystore = keystore

    def encrypt(self, plaintext: str, *, context: str) -> bytes:
        key = self._keystore.current()
        key_id = key.key_id.encode()
        nonce = os.urandom(NONCE_BYTES)
        sealed = AESGCM(key.material).encrypt(nonce, plaintext.encode(), context.encode())
        return bytes([VERSION, len(key_id)]) + key_id + nonce + sealed

    def decrypt(self, sealed: bytes, *, context: str) -> str:
        try:
            if sealed[0] != VERSION:
                raise TamperedCiphertext("Unknown ciphertext version.")
            id_end = 2 + sealed[1]
            key = self._keystore.get(sealed[2:id_end].decode())
            nonce, body = sealed[id_end : id_end + NONCE_BYTES], sealed[id_end + NONCE_BYTES :]
            return AESGCM(key.material).decrypt(nonce, body, context.encode()).decode()
        except (InvalidTag, UnknownKey, IndexError, UnicodeDecodeError) as error:
            raise TamperedCiphertext("This value can't be decrypted.") from error


def field_cipher(request: Request) -> FieldCipher:
    cipher: FieldCipher = request.app.state.field_cipher
    return cipher


Cipher = Annotated[FieldCipher, Depends(field_cipher)]
