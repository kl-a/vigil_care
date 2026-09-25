"""Contract tests for the identity interface. A future implementation (e.g. Entra ID) runs the same contract."""

import uuid

import pytest

from app.core.seams.identity import (
    DevLogin,
    DevLoginCredentials,
    IdentityProvider,
    LocalAccounts,
    LoginRefused,
    PasswordCredentials,
)

ACTIVE = uuid.uuid4()
INACTIVE = uuid.uuid4()


class Users:
    def is_active(self, user_id: uuid.UUID) -> bool:
        return user_id == ACTIVE


def refuses_what_it_cant_verify(provider: IdentityProvider) -> None:
    with pytest.raises(LoginRefused):
        provider.authenticate(PasswordCredentials("someone", "wrong", "000000"))
    with pytest.raises(LoginRefused):
        provider.authenticate(DevLoginCredentials(INACTIVE))


@pytest.mark.parametrize("provider", [DevLogin(Users()), LocalAccounts()], ids=["dev_login", "local_accounts"])
def test_every_provider_refuses_credentials_it_cant_verify(provider: IdentityProvider) -> None:
    refuses_what_it_cant_verify(provider)


def test_the_dev_login_accepts_an_active_user() -> None:
    assert DevLogin(Users()).authenticate(DevLoginCredentials(ACTIVE)) == ACTIVE


def test_local_accounts_refuse_everyone_until_stage_12() -> None:
    with pytest.raises(LoginRefused):
        LocalAccounts().authenticate(DevLoginCredentials(ACTIVE))
