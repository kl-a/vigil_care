# Vigil's Claude Project (MVP-1)

In MVP-1, extraction and trial matching run in a **Claude Project** on claude.ai, on **synthetic** Patients only. Each run takes one Patient's documents plus a trial export, and returns two files:
- **The run JSON:** what Vigil imports into the Clinical Record and a Match Run.
- **The Trial Briefing PDF:** rendered from that JSON.

```
claude-project/
├── project-instructions.md      paste into the Project's instructions
├── knowledge/                   upload all three to the Project's knowledge
│   ├── vigil-method.md          the method: extraction, the three-state engine, the Briefing layout
│   ├── vigil-run.schema.json    the contract Vigil's import validates against
│   └── trial-export-format.md   what the trial export file contains
├── prompt.md                    paste into a new chat for each run
├── patients/
│   ├── p1-dana-example/         EGFR L858R, post-osimertinib, 3 lines, new brain met
│   ├── p2-jordan-placeholder/   ALK+, treatment-naive, ECOG 1
│   └── p3-casey-fictional/      KRAS G12C, ECOG 2, prior melanoma 2023, CKD 3a
│       ├── documents/*.pdf      attach these to the chat
│       ├── expected.md          what a correct run finds (for you, not for Claude)
│       └── src/                 HTML sources; `patients/render.sh` rebuilds the PDFs
└── runs/                        save what Claude returns here
```

## 1. Set up the Project (once)

1. Go to **claude.ai → Projects → Create project**. Name it `Vigil runs (synthetic)`.
2. **Turn on file creation:** go to **Settings → Capabilities** and enable **Code execution and file creation**. Claude needs it to write the JSON and PDF as downloadable files.
3. **Add the instructions:** in the Project, open **Instructions** (or "Set project instructions") and paste the whole of [`project-instructions.md`](project-instructions.md).
4. **Add the knowledge:** in **Project knowledge**, upload the three files in [`knowledge/`](knowledge/). Don't upload Patient documents here; they go into each chat, so runs don't mix Patients.
5. **Choose the model:** select **Claude Opus 5.5** in the model picker for each chat.

## 2. Run one Patient

1. **Get the trial export** (`trials-<pseudonym>-<date>.json`) for this Patient from Vigil. This comes from MVP-1.1, the ClinicalTrials.gov Refresh; until it's built, there's no trial file to run with.
2. **Start a new chat** inside the Project. Use one chat per run.
3. **Attach** every PDF in `patients/<patient>/documents/` plus the trial export.
4. **Paste** the text under the line in [`prompt.md`](prompt.md), filling in the date and file names.
5. **Download** `run-<family_name>-<date>.json` and `briefing-<family_name>-<date>.pdf` into `runs/<patient>/`.
6. **Check against** `patients/<patient>/expected.md`. Note anything wrong in `runs/<patient>/notes.md`; those notes become prompt changes (bump `vigil-run-prompt@N` in both `prompt.md` and the schema's `prompt_version`).

## 3. Bring it back into Vigil

Upload the run JSON (and the PDF) on the Patient's **Trials** tab. The import is MVP-1.3 and the tab is MVP-1.4; neither is built yet. The import validates the JSON against the schema, refuses it if the Patient's name or DOB doesn't match, and writes:
- the Clinical Record rows (marked imported, unverified);
- the Match Run, with each trial's parsed criteria and Criterion Results.

## Rules

- **Synthetic only.** Never attach a real person's documents to this Project. That includes the example briefing in `docs/`, which is gitignored for that reason.
- **The schema is a contract.** If you change it, the import changes with it. Bump the version.
- **Rebuilding documents:** after editing `patients/p*_docs.py`, run `patients/render.sh`. It renders the PDFs in the Playwright Docker image, so there's nothing to install on the host.
