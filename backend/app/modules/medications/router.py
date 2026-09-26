"""The drug reference (#36). Refusals (403) come from the service."""

from fastapi import APIRouter

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.medications import drug_reference
from app.modules.medications.schemas import DrugOption

router = APIRouter(prefix="/drugs", tags=["medications"])


@router.get("")
def search_drugs(actor: SignedIn, db: Db, q: str = "") -> list[DrugOption]:
    """Drugs in the current PBS Schedule by generic or brand name, for picking a Medication."""
    return drug_reference.search(db, actor, q)
