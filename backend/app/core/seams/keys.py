"""Key interface (ADR 0003): where encryption keys come from. A local keystore now; Key Vault later.

Keys never live in the database. Each key has an id, recorded with every value it encrypts, so after a
rotation older values still open with the key that sealed them. Contract tests: tests/seams/test_keys.py.
"""

import base64
import binascii
import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

KEY_BYTES = 32  # AES-256


class UnknownKey(LookupError):
    """No key with that id: the value was sealed with a key this keystore doesn't hold."""


@dataclass(frozen=True)
class DataKey:
    key_id: str
    material: bytes = field(repr=False)


class Keystore(Protocol):
    def current(self) -> DataKey:
        """The key new values are encrypted with."""
        ...

    def get(self, key_id: str) -> DataKey:
        """A key by id, current or older; raises UnknownKey otherwise."""
        ...


class LocalKeystore:
    """Keys from the environment (`VIGIL_ENCRYPTION_KEY`, base64): one current key, plus older ones after a rotation."""

    def __init__(self, current: DataKey, previous: Iterable[DataKey] = ()) -> None:
        self._current = current
        self._keys = {key.key_id: key for key in (current, *previous)}

    @classmethod
    def from_secrets(cls, current: str, previous: Iterable[str] = ()) -> "LocalKeystore":
        return cls(_key(current), [_key(secret) for secret in previous])

    def current(self) -> DataKey:
        return self._current

    def get(self, key_id: str) -> DataKey:
        try:
            return self._keys[key_id]
        except KeyError:
            raise UnknownKey(key_id) from None


def _key(secret: str) -> DataKey:
    try:
        material = base64.b64decode(secret, validate=True)
    except (binascii.Error, ValueError):
        material = b""
    if len(material) != KEY_BYTES:
        raise ValueError("An encryption key must be a base64-encoded 256-bit (32-byte) key.")
    # A fingerprint, not the key: identifies which key sealed a value without revealing it.
    return DataKey(key_id="local-" + hashlib.sha256(b"vigil-key-id:" + material).hexdigest()[:12], material=material)
