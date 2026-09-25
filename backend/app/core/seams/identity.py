"""Identity interface (ADR 0003): who is logging in. Local implementations now; Entra ID later.

An implementation checks credentials and answers with the User's id; sessions are the app's job.
`DevLogin` exists only in dev (the startup guard and route registration enforce that). `LocalAccounts`
(password + TOTP 2FA) is a placeholder until login hardening in Stage 13 (design doc §15).
"""

import uuid
from dataclasses import dataclass
from typing import Protocol


class LoginRefused(Exception):
    """The credentials don't identify an active User. Deliberately says no more than that."""


@dataclass(frozen=True)
class DevLoginCredentials:
    user_id: uuid.UUID


@dataclass(frozen=True)
class PasswordCredentials:
    username: str
    password: str
    totp_code: str


Credentials = DevLoginCredentials | PasswordCredentials


class ActiveUsers(Protocol):
    """Answers whether a User may log in (exists, active, not soft-deleted)."""

    def is_active(self, user_id: uuid.UUID) -> bool: ...


class IdentityProvider(Protocol):
    def authenticate(self, credentials: Credentials) -> uuid.UUID:
        """The id of the User these credentials identify; raises LoginRefused otherwise."""
        ...


class DevLogin:
    """Dev only: choosing an active User is enough. No password, no 2FA."""

    def __init__(self, users: ActiveUsers) -> None:
        self._users = users

    def authenticate(self, credentials: Credentials) -> uuid.UUID:
        if not isinstance(credentials, DevLoginCredentials) or not self._users.is_active(credentials.user_id):
            raise LoginRefused()
        return credentials.user_id


class LocalAccounts:
    """Password + TOTP 2FA login. Built in Stage 13; until then it refuses everyone."""

    def authenticate(self, credentials: Credentials) -> uuid.UUID:
        raise LoginRefused()
