"""The complete schema metadata, for Alembic, the drift test and the data-model diagram.

This is tooling, not runtime Core code: it imports every module's models (Core and Specialty
Modules) so that `Base.metadata` holds every table. Runtime code reaches modules only through the
module registry (design doc §4.1).
"""

# Imported for their side effect: each models module registers its tables on Base.metadata.
import app.audit.models  # noqa: F401
import app.llm.models  # noqa: F401
import app.modules.accounts.models  # noqa: F401
import app.modules.clinical.models  # noqa: F401
import app.modules.deid.models  # noqa: F401
import app.modules.documents.models  # noqa: F401
import app.modules.extraction.models  # noqa: F401
import app.modules.matching.models  # noqa: F401
import app.modules.medications.models  # noqa: F401
import app.modules.ocr.models  # noqa: F401
import app.modules.patients.models  # noqa: F401
import app.modules.pbs.models  # noqa: F401
import app.modules.practice.models  # noqa: F401
import app.modules.registry.models  # noqa: F401
import app.modules.reports.models  # noqa: F401
import app.modules.trials.models  # noqa: F401
import app.orchestrator.models  # noqa: F401
import app.specialties.oncology.models  # noqa: F401
from app.core.base_model import Base

metadata = Base.metadata
