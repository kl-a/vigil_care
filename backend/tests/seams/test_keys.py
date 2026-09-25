"""Key interface (ADR 0003): contract tests any Keystore must pass, local keystore today, Key Vault later.

A new implementation joins by adding a factory to KEYSTORES.
"""

import base64
from collections.abc import Callable

import pytest

from app.core.seams.keys import Keystore, LocalKeystore, UnknownKey

SECRET = base64.b64encode(bytes(range(32))).decode()
OLDER = base64.b64encode(bytes(range(32, 64))).decode()

KEYSTORES: dict[str, Callable[[], Keystore]] = {
    "local": lambda: LocalKeystore.from_secrets(SECRET),
    "local, rotated": lambda: LocalKeystore.from_secrets(SECRET, previous=[OLDER]),
}


@pytest.fixture(params=KEYSTORES)
def keystore(request: pytest.FixtureRequest) -> Keystore:
    return KEYSTORES[request.param]()


def test_the_current_key_is_256_bits(keystore: Keystore) -> None:
    assert len(keystore.current().material) == 32


def test_a_key_is_found_again_by_its_id(keystore: Keystore) -> None:
    key = keystore.current()
    assert keystore.get(key.key_id) == key


def test_the_current_key_is_stable(keystore: Keystore) -> None:
    assert keystore.current() == keystore.current()


def test_an_unknown_key_id_is_refused(keystore: Keystore) -> None:
    with pytest.raises(UnknownKey):
        keystore.get("no-such-key")


def test_a_key_id_never_reveals_the_key(keystore: Keystore) -> None:
    key = keystore.current()
    assert key.key_id.encode() not in key.material
    assert base64.b64encode(key.material).decode() not in key.key_id


# --- The local keystore specifically --------------------------------------------------------------


def test_after_rotation_older_keys_are_still_found() -> None:
    rotated = LocalKeystore.from_secrets(SECRET, previous=[OLDER])
    older = LocalKeystore.from_secrets(OLDER).current()
    assert rotated.current() != older
    assert rotated.get(older.key_id) == older


@pytest.mark.parametrize("bad", ["", "not base64!", base64.b64encode(b"too short").decode()])
def test_a_secret_that_isnt_a_256_bit_key_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="256-bit"):
        LocalKeystore.from_secrets(bad)
