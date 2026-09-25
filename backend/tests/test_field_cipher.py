"""Field encryption (design doc §6.2): AES-256-GCM, the key from the key interface, never in the database."""

import base64

import pytest

from app.core.crypto import FieldCipher, TamperedCiphertext
from app.core.seams.keys import LocalKeystore

KEY = base64.b64encode(bytes(range(32))).decode()
NEWER = base64.b64encode(bytes(range(64, 96))).decode()
CIPHER = FieldCipher(LocalKeystore.from_secrets(KEY))


def test_a_value_round_trips() -> None:
    sealed = CIPHER.encrypt("0000 12345 1", context="patient_identity.medicare_number:p-1")
    assert CIPHER.decrypt(sealed, context="patient_identity.medicare_number:p-1") == "0000 12345 1"


def test_the_plaintext_isnt_in_the_ciphertext_and_each_encryption_differs() -> None:
    first = CIPHER.encrypt("0000 12345 1", context="c")
    second = CIPHER.encrypt("0000 12345 1", context="c")
    assert b"12345" not in first
    assert first != second


def test_a_value_moved_to_another_field_or_patient_wont_decrypt() -> None:
    sealed = CIPHER.encrypt("0000 12345 1", context="patient_identity.medicare_number:p-1")
    with pytest.raises(TamperedCiphertext):
        CIPHER.decrypt(sealed, context="patient_identity.medicare_number:p-2")
    with pytest.raises(TamperedCiphertext):
        CIPHER.decrypt(sealed, context="patient_identity.phone:p-1")


def test_tampering_is_detected() -> None:
    sealed = bytearray(CIPHER.encrypt("0000 12345 1", context="c"))
    sealed[-1] ^= 1
    with pytest.raises(TamperedCiphertext):
        CIPHER.decrypt(bytes(sealed), context="c")


def test_values_sealed_before_a_key_rotation_still_open() -> None:
    sealed = CIPHER.encrypt("0491 570 156", context="c")
    rotated = FieldCipher(LocalKeystore.from_secrets(NEWER, previous=[KEY]))
    assert rotated.decrypt(sealed, context="c") == "0491 570 156"
    assert rotated.encrypt("x", context="c") != CIPHER.encrypt("x", context="c")
