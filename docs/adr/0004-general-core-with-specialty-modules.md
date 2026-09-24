# A general clinical core with pluggable Specialty Modules; oncology first

Vigil will serve more than oncology over time: next private outpatient specialists, then general practice, and hospitals only in the future. Every clinical requirement so far comes from one oncology practice, so we build the MVP for oncology only. But we split it into a **specialty-agnostic core** (Patients, Documents, the ingestion and de-identification pipeline, Verification, Conditions, Medications, labs, imaging, the Patient Summary shell, trial matching engine, exports) and **Specialty Modules** that plug in at fixed points. Oncology is the first module and holds everything cancer-specific. New specialties are added one at a time, each after research and requirements gathering with a clinician from that specialty. Retrofitting this split after the clinical tables were built would be expensive; doing it before any code exists costs almost nothing.

The pattern is a **plugin architecture**: a single Specialty Module contract, a module registry, a Strategy at each extension point, and per-Practice activation. We chose it over Builder, which fits assembling one complex object, not extending a system at fixed points. Builder may still be used to assemble a Practice's configuration from its enabled modules.

## Considered Options

- **Generalise the whole product now.** Rejected: there are no non-oncology clinicians to design against yet.
- **Stay oncology-only and revisit later.** Rejected: the cancer-specific model would be baked into the core tables and screens.

## Consequences

- The core must not import any Specialty Module. It reaches modules only through the registry.
- Module tables are created by ordinary migrations and always exist; activation per Practice only switches behaviour and UI. Deactivating a module hides its data and never deletes it.
- The trial matching engine is core, and each module supplies its trial-criteria vocabulary. Treatment Options are optional per module, because most specialties have no free guideline source like eviQ.
- **Portability rule:** each concept (e.g. Line of Therapy, Response Assessment) is one self-contained unit (tables, schemas, prompts, rules, evaluators, UI section) behind its own interface, with tests at that interface. Moving it between modules, or into the Core, is then a mechanical move rather than a rewrite.
- Hospitals will need an Organisation-with-departments model beyond Practice. That is future work and not designed for now.
