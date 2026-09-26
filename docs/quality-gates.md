# Quality Gates

What must pass before any change to a model, prompt, OCR engine or pipeline is deployed. The document gates run against the **Reference Set** (see [CONTEXT.md](../CONTEXT.md)). The set contains only synthetic documents, annotated independently by Dr De Souza and an in-house User. Disagreements between the two are resolved before the set is locked.

## What the Reference Set contains

1. **Readable documents** with known correct Extracted Facts and known PII positions, covering every launch Document Type and every input type (native PDF, scan, fax, phone photo).
2. **Deliberately unreadable documents**, e.g. illegible handwriting, a blank or smudged fax, a heavily blurred photo. The expected result is that they are **routed to manual review with no Extracted Facts**. Vigil fails the gate if it "reads" anything from them, since that shows it is producing values that aren't on the page.
3. **Leak-test variants** of the readable documents (see below).

## Gates

| Gate | Pass condition |
|---|---|
| Unreadable routing | Every deliberately unreadable document is routed to manual review, and none produces Extracted Facts. |
| Extraction accuracy | No drop from the previous release in any fact category (labs, medications, Biomarkers, …), plus an absolute floor for numeric values. *(Thresholds still to be set.)* |
| PII detection, cloud-eligible | On readable documents, 100% of planted PII is either masked or sent to manual redaction. Nothing may escalate to the cloud until this passes. |
| PII detection, local only | A lower target is acceptable for processing that never leaves the Practice Boundary. *(Threshold still to be set.)* |
| Masking leak tests | Zero PII can be recovered from any masked output. |
| No Patient data in support data | A synthetic Patient with a distinctive name and identifiers goes through the Patient flows (create, edit identity, Care Team, remove), a Job about them fails with their name in the error, and a Refresh runs. None of their values appears in any support endpoint's output (every route tagged `support`, read as staff and as a developer admin) or in the application logs (design doc §6.4). |

`make gates` runs every gate in the test environment (`VIGIL_ENV=test`). The Reference Set gates arrive with the document pipeline. The no-Patient-data gate is the backend test `backend/tests/api/test_no_patient_data_in_support.py`, which runs against a freshly migrated database in the test Postgres, so start it first with `make test-db`. The same test also runs with the backend tests.

## Masking leak tests

For every masked output, try to recover the original PII by each of these routes, and expect nothing:

- Re-run OCR on the masked image.
- Extract the PDF text layer, including any hidden OCR text under the image.
- Read the PDF metadata, XMP, title, bookmarks, form fields, attachments and incremental-save history.
- Read the EXIF metadata and the filename.
- Decode any barcodes or QR codes.
- Test **rotated** pages (90/180/270°) and pages with CropBox/MediaBox offsets, which is where box positions tend to drift.
- Test pages that were **downscaled** or normalised before masking.
- Run Free Law Project's x-ray, which detects black boxes drawn over text that is still present.

## Guardrails apply from v1

v1 processes synthetic data only, but every guardrail runs exactly as it will in prod. Nothing is relaxed because the data is fake: de-identification before anything leaves the Practice Boundary, human Verification, per-fact review, the leak tests, and every gate above.

## Go-live checklist (prod is its own milestone after v1)

- [ ] Every gate above passes on the Reference Set.
- [ ] Redaction has been validated on realistic faxes and photos (§9.4) in test.
- [ ] Items in [revisit-later.md](revisit-later.md) marked as needing resolution before real patients are closed (Presidio maturity, eviQ terms of use).
- [ ] Retention periods and the handling of deletion requests are decided ([revisit-later.md](revisit-later.md) #15).
- [ ] Dr De Souza has signed off the treatment matching walkthrough ([revisit-later.md](revisit-later.md) #10).
- [ ] The runbook is written and followed for the prod environment: secrets and their rotation, upgrades, Refreshes, backups and restore tests, Users, incidents ([#32](https://github.com/kl-a/vigil_care/issues/32), [revisit-later.md](revisit-later.md) #25).
- [ ] Where prod's data and secrets live is decided and recorded in an ADR: each Practice's data kept apart, one shared store for Shared Reference Data, secrets in a secret manager, never in the repo ([revisit-later.md](revisit-later.md) #26).
