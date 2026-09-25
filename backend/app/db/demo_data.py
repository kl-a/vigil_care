"""Synthetic demo Practice for stage demos (design doc §15). Dev only.

    python -m app.db.demo_data      # or: make demo-data

Every name comes from the frontend brief §10 ("use only this; no real people"). Loading is idempotent:
rows have fixed ids, and anything already there is left alone. Later stages add Patients, Providers
and Clinical Records here.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.audit.models import Verification
from app.core.config import Settings
from app.core.database import session_factory
from app.db import metadata  # noqa: F401  (registers every table, so foreign keys resolve)
from app.modules.accounts.models import User
from app.modules.practice.models import Practice
from app.modules.registry.models import PracticeModule

NAMESPACE = uuid.UUID("5b0f3c1e-0d6a-4a5e-9c1b-7a1d2c3e4f50")
PRACTICE_ID = uuid.uuid5(NAMESPACE, "practice")
# Not a password hash: nobody can sign in with a password until Stage 12, and then only after enrolment.
NO_PASSWORD = "!demo-user-dev-login-only"


class DemoDataRefused(RuntimeError):
    """Demo data is synthetic and belongs only in dev."""


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    job_title: str

    @property
    def id(self) -> uuid.UUID:
        return uuid.uuid5(NAMESPACE, f"user:{self.username}")


USERS = (
    DemoUser("alex.rivera", "Dr Alex Rivera", "clinician"),
    DemoUser("sam.lee", "Sam Lee", "trial_coordinator"),
    DemoUser("jordan.park", "Jordan Park", "secretary"),
    DemoUser("casey.dev", "Casey Dev", "developer_admin"),
)
DEVELOPER_ADMIN = USERS[3]


def load(settings: Settings) -> None:
    if settings.environment != "dev":
        raise DemoDataRefused(f"Demo data is for dev only, not '{settings.environment}'.")
    with session_factory(settings.database_url).begin() as db:
        _practice(db)
        for user in USERS:
            _user(db, user)
        _activate_oncology(db)


def _practice(db: Session) -> None:
    if db.get(Practice, PRACTICE_ID) is None:
        db.add(
            Practice(
                id=PRACTICE_ID,
                name="Harbourside Oncology (synthetic)",
                address="1 Example St, Sydney NSW 2000",
            )
        )
        db.flush()


def _user(db: Session, user: DemoUser) -> None:
    if db.get(User, user.id) is None:
        db.add(
            User(
                id=user.id,
                practice_id=PRACTICE_ID,
                username=user.username,
                display_name=user.display_name,
                password_hash=NO_PASSWORD,
                job_title=user.job_title,
            )
        )
        db.flush()


def _activate_oncology(db: Session) -> None:
    """Activated by the developer admin, with the Verification a real activation writes (§4.1)."""
    activation_id = uuid.uuid5(NAMESPACE, "practice_module:oncology")
    if db.get(PracticeModule, activation_id) is not None:
        return
    db.add(
        PracticeModule(
            id=activation_id,
            practice_id=PRACTICE_ID,
            module_key="oncology",
            is_active=True,
            changed_by_user_id=DEVELOPER_ADMIN.id,
        )
    )
    db.add(
        Verification(
            practice_id=PRACTICE_ID,
            subject_table="practice_module",
            subject_id=activation_id,
            user_id=DEVELOPER_ADMIN.id,
            job_title_at_time=DEVELOPER_ADMIN.job_title,
            action="activate_module",
            reason="Demo data",
            after={"module_key": "oncology", "is_active": True},
        )
    )


def main() -> None:
    load(Settings())
    print("Loaded the synthetic demo Practice: Harbourside Oncology (synthetic).")
    for user in USERS:
        print(f"  {user.display_name:<16} {user.job_title}")


if __name__ == "__main__":
    main()
