"""Synthetic demo Practices for stage demos (design doc §15). Dev only.

    python -m app.db.demo_data      # or: make demo-data

Every name comes from the frontend brief §10 ("use only this; no real people"), marked "(synthetic)".
Harbourside Oncology is the main demo Practice, with one User per Job Title. Northside Oncology is a second
Practice where Dr Alex Rivera also works, so one login with several Practice Memberships is demoable.

Loading is idempotent: rows have fixed ids; existing rows are kept (User names are brought up to date). Later
stages add Patients, Providers and Clinical Records here.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import Verification
from app.core.config import Settings
from app.core.database import session_factory
from app.core.vocabulary import JobTitle
from app.db import metadata  # noqa: F401  (registers every table, so foreign keys resolve)
from app.modules.accounts.models import PracticeMembership, User
from app.modules.practice.models import Practice, Site
from app.modules.registry.models import PracticeModule

NAMESPACE = uuid.UUID("5b0f3c1e-0d6a-4a5e-9c1b-7a1d2c3e4f50")
PRACTICE_ID = uuid.uuid5(NAMESPACE, "practice")  # Harbourside, the main demo Practice
NORTHSIDE_ID = uuid.uuid5(NAMESPACE, "practice:northside")
# Not a password hash: nobody can sign in with a password until Stage 13, and then only after enrolment.
NO_PASSWORD = "!demo-user-dev-login-only"


class DemoDataRefused(RuntimeError):
    """Demo data is synthetic and belongs only in dev."""


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    job_title: JobTitle  # at Harbourside

    @property
    def id(self) -> uuid.UUID:
        return uuid.uuid5(NAMESPACE, f"user:{self.username}")


USERS = (
    DemoUser("alex.rivera", "Dr Alex Rivera (synthetic)", "clinician"),
    DemoUser("sam.lee", "Sam Lee (synthetic)", "trial_coordinator"),
    DemoUser("jordan.park", "Jordan Park (synthetic)", "secretary"),
    DemoUser("casey.dev", "Casey Dev (synthetic)", "developer_admin"),
)
DEVELOPER_ADMIN = next(user for user in USERS if user.job_title == "developer_admin")
CLINICIAN = next(user for user in USERS if user.job_title == "clinician")


def load(settings: Settings) -> None:
    if settings.environment != "dev":
        raise DemoDataRefused(f"Demo data is for dev only, not '{settings.environment}'.")
    with session_factory(settings.database_url).begin() as db:
        _practice(db, PRACTICE_ID, HARBOURSIDE)
        _practice(db, NORTHSIDE_ID, NORTHSIDE)
        for user in USERS:
            _user(db, user)
            _membership(db, PRACTICE_ID, user, user.job_title)
        # Dr Alex Rivera also consults at Northside: one login, a second Membership (#24).
        _membership(db, NORTHSIDE_ID, CLINICIAN, "clinician")
        for site in SITES:
            _site(db, site)
        _activate_oncology(db)


# Frontend brief §10. 02 5550 xxxx is reserved for fiction, example.com never resolves, and an ABN of all
# zeros is never issued.
HARBOURSIDE = {
    "name": "Harbourside Oncology (synthetic)",
    "address": "1 Example St, Sydney NSW 2000",
    "phone": "02 5550 0100",
    "fax": "02 5550 0101",
    "email": "reception@harbourside-oncology.example.com",
    "abn": "00 000 000 000",
}
NORTHSIDE = {
    "name": "Northside Oncology (synthetic)",
    "address": "2 Example Rd, Chatswood NSW 2067",
    "phone": "02 5550 0200",
    "fax": "02 5550 0201",
    "email": "reception@northside-oncology.example.com",
    "abn": "00 000 000 000",
}


@dataclass(frozen=True)
class DemoSite:
    practice_id: uuid.UUID
    name: str
    address: str
    lat: Decimal
    lng: Decimal
    is_primary: bool = False

    @property
    def id(self) -> uuid.UUID:
        return uuid.uuid5(NAMESPACE, f"site:{self.practice_id}:{self.name}")


# Trial-site distances (Stage 10) are measured from each Site. Harbourside also runs a hospital clinic.
SITES = (
    DemoSite(PRACTICE_ID, "Harbourside rooms", "1 Example St, Sydney NSW 2000", Decimal("-33.8688"), Decimal("151.2093"), is_primary=True),
    DemoSite(PRACTICE_ID, "Example Hospital clinic", "2 Example Rd, Camperdown NSW 2050", Decimal("-33.8898"), Decimal("151.1873")),
    DemoSite(NORTHSIDE_ID, "Northside rooms", "2 Example Rd, Chatswood NSW 2067", Decimal("-33.7969"), Decimal("151.1803"), is_primary=True),
)


def _practice(db: Session, practice_id: uuid.UUID, details: dict[str, str]) -> None:
    practice = db.get(Practice, practice_id)
    if practice is None:
        db.add(Practice(id=practice_id, **details))
        db.flush()
        return
    for field, value in details.items():  # fill in what older demo databases lack
        if getattr(practice, field) is None:
            setattr(practice, field, value)


def _site(db: Session, site: DemoSite) -> None:
    # Databases migrated from before #25 already have a primary Site per Practice (from its old location).
    has_primary = db.scalars(select(Site.id).where(Site.practice_id == site.practice_id, Site.is_primary)).first()
    if db.get(Site, site.id) is not None or (site.is_primary and has_primary is not None):
        return
    db.add(
        Site(
            id=site.id,
            practice_id=site.practice_id,
            name=site.name,
            address=site.address,
            lat=site.lat,
            lng=site.lng,
            is_primary=site.is_primary,
        )
    )
    db.flush()


def _user(db: Session, user: DemoUser) -> None:
    existing = db.get(User, user.id)
    if existing is not None:
        existing.display_name = user.display_name  # keeps older demo databases in step with the names here
        return
    db.add(User(id=user.id, username=user.username, display_name=user.display_name, password_hash=NO_PASSWORD))
    db.flush()


def _membership(db: Session, practice_id: uuid.UUID, user: DemoUser, job_title: JobTitle) -> None:
    # Looked up by person and Practice: databases migrated from before #24 gave Memberships random ids.
    existing = db.scalars(
        select(PracticeMembership).where(PracticeMembership.practice_id == practice_id, PracticeMembership.user_id == user.id)
    ).one_or_none()
    if existing is None:
        db.add(PracticeMembership(practice_id=practice_id, user_id=user.id, job_title=job_title))
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
    print(f"Loaded the synthetic demo Practices: {HARBOURSIDE['name']} and {NORTHSIDE['name']}.")
    for user in USERS:
        print(f"  {user.display_name:<28} {user.job_title}")
    print(f"  {CLINICIAN.display_name:<28} also clinician at {NORTHSIDE['name']}")


if __name__ == "__main__":
    main()
