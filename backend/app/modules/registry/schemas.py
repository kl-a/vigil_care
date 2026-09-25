from pydantic import BaseModel


class ModuleStatus(BaseModel):
    key: str
    display_name: str
    version: str
    is_active: bool


class ModuleChange(BaseModel):
    is_active: bool
    reason: str | None = None


class ActiveSectionOut(BaseModel):
    module: str
    id: str
    slot: str
    title: str
    order: int


class ActiveTabOut(BaseModel):
    module: str
    segment: str
    label: str


class ActiveConfiguration(BaseModel):
    """What the frontend shows for this Practice: active modules, their sections and Patient tabs."""

    active_modules: list[str]
    sections: list[ActiveSectionOut]
    patient_tabs: list[ActiveTabOut]
