"""Practice module service interface: what other modules may ask about Practices."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.practice.models import Practice


def practice_names(db: Session, practice_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    rows = db.execute(select(Practice.id, Practice.name).where(Practice.id.in_(practice_ids)))
    return {practice_id: name for practice_id, name in rows}
