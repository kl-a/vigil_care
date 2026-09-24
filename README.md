# Vigil

**Clinical decision support for medical practices, starting with oncology.** Vigil turns patient documents (scanned letters, faxes, phone photos, PDFs) into a verified, structured clinical record. It then shows the clinician standard-of-care treatment options, PBS drug information and matching clinical trials to review. The clinician decides; Vigil only informs.

> **Status: design complete, build starting.** There's no application code yet. The MVP runs locally on synthetic data only, and nothing here is ready for real patient data.

## What it does

- **Document ingestion.** Local OCR reads scans and faxes. Personal information is found and masked before anything leaves the practice. Each extracted value is reviewed and signed off individually by staff before it enters the Clinical Record.
- **Patient Summary.** A one-page, consultation-ready view: each diagnosis with its stage, biomarkers and recurrences; the latest results and scans; current treatment; comorbidities and medications; the management plan; and open items.
- **Treatment Options.** eviQ standard-of-care protocols matched to a diagnosis, with PBS listing and coverage per drug.
- **Trial matching.** ClinicalTrials.gov and ANZCTR trials, sorted into Potentially Eligible, Needs Information or Excluded, with evidence for every criterion.
- **Redaction.** Standalone de-identification of documents for trial portals and referrals.

## Principles

- **Clinical decision support, not decision making.** Vigil operates under the TGA CDSS exemption. It never recommends; every output is for clinician review.
- **Identifiable data never leaves the practice.** Anything sent to a cloud model is masked or pseudonymised first ([ADR 0001](docs/adr/0001-deidentify-before-leaving-practice.md)).
- **A human verifies everything.** No value reaches the Clinical Record without a named person's sign-off, and sign-off rights depend on Job Title.
- **Built local, ready for the cloud.** Infrastructure sits behind swappable interfaces so it can move to Azure later ([ADR 0003](docs/adr/0003-local-mvp-with-cloud-seams.md)).

## Documentation

| Doc | What it's for |
|---|---|
| [docs/Vigil_Design_Document.md](docs/Vigil_Design_Document.md) | The full technical design (v1.3): architecture, data model, pipeline, API, build order |
| [CONTEXT.md](CONTEXT.md) | Glossary. All code, UI and issues use these terms. |
| [docs/frontend-design.md](docs/frontend-design.md) | Frontend brief: tokens, app shell, components, screen specs |
| [docs/adr/](docs/adr/) | Architecture decisions |
| [docs/quality-gates.md](docs/quality-gates.md) | Reference Set, deployment gates, masking leak tests, go-live checklist |
| [docs/hardware-options.md](docs/hardware-options.md) | Where the OCR and vision models can run |
| [docs/revisit-later.md](docs/revisit-later.md) | Provisional decisions and deferred scope |

## Planned stack

Next.js 14 + TypeScript + Tailwind/shadcn/ui · Python 3.12 + FastAPI · PostgreSQL 16 · PaddleOCR (PP-OCRv5) + docTR + PaddleOCR-VL for local OCR · Presidio for PII detection · Docker Compose. See design doc §3.

## Work tracking

Work is tracked in [GitHub Issues](https://github.com/kl-a/vigil_care/issues). The spec for the first milestone (Phase 0 + 1: scaffold, logins, Practice and Patients) is [#1](https://github.com/kl-a/vigil_care/issues/1), and its tickets are linked from there. Start with [#11](https://github.com/kl-a/vigil_care/issues/11), the walking skeleton.

## Getting started

Not yet. Setup instructions will arrive with the walking skeleton ([#11](https://github.com/kl-a/vigil_care/issues/11)). Once it lands, the whole stack will start with `docker compose up`. Nothing is installed on the host except Docker, Node.js and Python.
