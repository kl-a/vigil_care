"""The complete schema metadata, for Alembic, the drift test and the data-model diagram.

This is tooling, not runtime Core code: it imports every module's models (Core and Specialty
Modules) so that `Base.metadata` holds every table. Runtime code reaches modules only through the
module registry (design doc §4.1).
"""

from app.audit import models as audit_models
from app.core.base_model import Base
from app.llm import models as llm_models
from app.modules.accounts import models as accounts_models
from app.modules.clinical import models as clinical_models
from app.modules.deid import models as deid_models
from app.modules.documents import models as documents_models
from app.modules.extraction import models as extraction_models
from app.modules.matching import models as matching_models
from app.modules.medications import models as medications_models
from app.modules.ocr import models as ocr_models
from app.modules.patients import models as patients_models
from app.modules.pbs import models as pbs_models
from app.modules.practice import models as practice_models
from app.modules.registry import models as registry_models
from app.modules.reports import models as reports_models
from app.modules.trials import models as trials_models
from app.orchestrator import models as orchestrator_models
from app.specialties.oncology import models as oncology_models

MODEL_MODULES = (
    practice_models,
    accounts_models,
    patients_models,
    registry_models,
    documents_models,
    ocr_models,
    extraction_models,
    audit_models,
    clinical_models,
    medications_models,
    pbs_models,
    trials_models,
    matching_models,
    deid_models,
    llm_models,
    reports_models,
    orchestrator_models,
    oncology_models,
)

metadata = Base.metadata
