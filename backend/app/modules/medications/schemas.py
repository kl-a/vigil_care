import uuid

from pydantic import BaseModel


class DrugOption(BaseModel):
    """A drug the Medication Manager can pick, from the drug reference."""

    id: uuid.UUID
    generic_name: str
    brand_names: list[str]
    atc_code: str | None
    is_cancer_drug: bool
    # Its PBS Items in the current schedule; any of them opens the drug in the PBS Drug Lookup.
    pbs_item_codes: list[str]
