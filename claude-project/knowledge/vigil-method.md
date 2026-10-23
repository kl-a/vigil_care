# Vigil method: extraction, trial matching and the Trial Briefing

This is how a Vigil run is done. Follow it exactly. Output must validate against `vigil-run.schema.json`.

## 0. Ground rules

- **Decision support, not decision making.** You describe; the clinician decides. Never write "eligible", "recommended", "pursue", "should enrol", "verdict" or "best option". Write "Potentially Eligible", "Needs Information", "meets", "does not meet", "not documented".
- **Only what the documents say.** Every Clinical Record fact carries a verbatim quote from an input document. If a value isn't stated, it's missing: put it in `gaps`, never infer it. ECOG in particular is never inferred from "well" or "active".
- **Only trials from the trial export.** Every `nct_id`, title, sponsor, phase, status, site and distance comes from the attached trial export file. Never add a trial from memory or the web, never change a site's status, never invent a distance.
- **No literature.** Don't cite studies, response rates or journals. Mechanism comes from the trial record only.
- **Synthetic data only.** These Patients are fictional. If anything looks like a real person's record, stop and say so.

## 1. Extraction → `clinical_record`

Read every document. For each fact kind in the schema, add one item per distinct fact, with:
- `ref`: a run-local id: `cond1`, `cd1`, `bm1`, `rec1`, `tc1`, `med1`, `lab1`, `img1`, `fnd1`, `ra1`, `ps1`, `cns1`, `mp1`, `note1`.
- `source`: one or more `{doc_id, quote}`; `doc_id` is the file name exactly as uploaded; `quote` is copied verbatim (short is fine).
- `confidence`: `high` when stated plainly; `medium` when stated but ambiguous (e.g. two documents disagree; say which in a later fact's quote); `low` when the reading is uncertain.

Specifics:
- **Every cancer is a Cancer Diagnosis**, current or past (a melanoma excised years ago is `cancer_status: no_evidence_of_disease`). Non-cancer conditions go in `conditions`.
- **Biomarkers:** one row per gene/marker result, negatives included. Link each to its Cancer Diagnosis. PD-L1 TPS goes in `value_num` with `value_unit: "%"`.
- **Treatment Courses:** oldest first. `line_of_therapy` only for palliative systemic courses, counting from 1 in the metastatic setting. Put the drugs in `drugs`.
- **Labs:** latest of each analyte, plus earlier values when they show a trend. Use the report's own reference range and flag.
- **Imaging:** one `imaging_studies` item per report; lesions as `findings` with size in mm; a stated response (e.g. "progressive disease") as a `response_assessments` item with `source: radiology_report`. A clinician's stated response in a letter is `source: clinician`.
- **CNS:** whenever brain imaging or a letter states brain status, add a `cns_status` item (present / treated / symptomatic / on steroids, as stated; leave unknowns null).
- **Management Plan:** verbatim.
- **Dates:** ISO `YYYY-MM-DD`. If only month and year are given, use the 1st and say so in the quote's context by keeping the original wording in the quote.

## 2. The target Condition

The trials are matched for **one** Cancer Diagnosis: the active one the documents are about. Put its `ref` in `run.target_cancer_diagnosis_ref`.

## 3. Matching: the three-state engine

For **every** trial in the export:

1. **Parse** its eligibility text into criteria. One criterion per gating rule, `raw_text` copied verbatim, `kind` inclusion/exclusion, an `attribute` from the vocabulary below, and a `scope`:
   - `target_condition`: about the cancer being matched (histology, Biomarkers, Line of Therapy, prior lines, Disease Extent, Stage).
   - `whole_person`: about the Patient as a whole (age, sex, ECOG, organ function, other Conditions, **other malignancies**, CNS status, washout).
2. **Pre-filter deterministically first** on structured facts: age (from DOB at `generated_on`), sex, ECOG, required Biomarkers, number of prior systemic lines, Disease Extent, histology, other malignancies with dates, CNS flags, lab thresholds. Then **adjudicate** the remaining free-text criteria against the Clinical Record.
3. **Criterion Result** for each criterion: `MET`, `NOT_MET` or `UNKNOWN`.
   - **MET always means "does not stand in the way".** For an exclusion, MET means the exclusion does not apply. "No other malignancy within 5 years" is NOT_MET for a Patient whose melanoma was treated 3 years ago.
   - **Missing data is UNKNOWN, never assumed.**
   - `rationale`: one or two sentences, concrete (values, dates).
   - `patient_evidence`: the `ref`s relied on.
4. **Washout:** quote the trial's rule; take this Patient's most recent anticancer therapy and its end date from `treatment_courses`; MET if the gap to `generated_on` already satisfies the rule, NOT_MET if it can't be satisfied by waiting, UNKNOWN if dates are missing. Also add it as a `washout` criterion.
5. **Match State:**
   - any criterion NOT_MET → `EXCLUDED`
   - else any UNKNOWN → `NEEDS_INFORMATION`
   - else → `POTENTIALLY_ELIGIBLE`

**Attribute vocabulary:** `age`, `sex`, `ecog`, `prior_systemic_lines`, `required_biomarker`, `pd_l1_tps`, `brain_mets_status`, `leptomeningeal_disease`, `measurable_disease`, `organ_function`, `prior_immunotherapy`, `prior_targeted_therapy`, `hormone_receptor_status`, `her2_status`, `disease_extent_required`, `stage_at_diagnosis`, `histology_required`, `other_malignancy_within_years`, `condition_exclusion`, `washout`, `other` (use `other` sparingly: consent, contraception, life expectancy and similar administrative criteria may be grouped into one `other` criterion).

`measurable_disease` is judged from `findings` (`is_measurable`, `size_mm`).

## 4. What goes in `trials` and `not_shown`

- `trials`: POTENTIALLY_ELIGIBLE and NEEDS_INFORMATION trials, at most 8, ordered by Match State (Potentially Eligible first), then Site Access (a recruiting site nearest first), then fewest UNKNOWN.
- `not_shown`: every EXCLUDED trial with the one deciding criterion as `reason` (e.g. "Requires ALK rearrangement; ALK not detected"), plus any surplus beyond 8.
- **Site Access** lists the trial's Australian sites from the export, nearest first, with their status and `distance_km` copied from the export.
- **Mechanism** from the trial record's interventions and summary.
- **Summary**: 1–3 sentences of observations: what's met, what gates it (the UNKNOWNs that matter), and access. Example: "Criteria largely met; gated on brain-metastasis stability and the pleural effusion criterion. Nearest site recruiting, ~14 km."

## 5. The Trial Briefing document

Render it **from the JSON**, after the JSON is final; never add anything that isn't in the JSON. A PDF, A4 portrait, plain and readable:

1. **Header** on page 1: "Clinical Trial Options: Discussion Briefing"; Patient name and DOB; "Prepared {generated_on} by Vigil (synthetic test run)"; the line "Decision support only: confirm with the treating oncologist and trial coordinator" in every page footer.
2. **Page 1: Current condition (snapshot).** The `snapshot` paragraphs, each with a bold lead-in (Diagnosis. Prior systemic therapy. Disease sites. CNS. Labs / organ function. Tissue / performance status.), `time_sensitive` highlighted if present, then **Gaps** as a short list.
3. **Page 2: Side by side.** One row per trial in `trials`: Trial (NCT id), Mechanism, Phase, Closest site · status · distance, Match State and the main gating item. Row colour: green = Potentially Eligible with a recruiting site; amber = Needs Information, or no recruiting site within 50 km; red = no recruiting Australian site. A key under the table says exactly this. Then **Not shown** as a short list from `not_shown`.
4. **One page per trial:** title "{n}. {nct_id}: {mechanism}"; a facts table (Sponsor, Phase, Overall status, Sites with status and distance, Washout from {this Patient's last therapy}, CNS rule); then **Compatibility** with each criterion as a bullet marked ● Meets (green), ● Confirm / unknown (amber), ● Barrier (red), with its rationale; then a **Summary** box.

Don't add a "Verdict", recommendations, literature or evidence sections.
