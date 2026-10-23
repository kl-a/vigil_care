# Expected: Dana Example (synthetic)

Use this to check a run. "Must" items are errors if missed; "Watch" items are where a careless run goes wrong.

## Clinical Record (must)
- **Cancer Diagnoses (2):**
  - NSCLC, adenocarcinoma, right upper lobe, dx 2024-01, stage IV, metastatic, active. This is the **target**.
  - Breast cancer (left IDC, T1N0, ER/PR+, HER2−), dx 2017, `no_evidence_of_disease`.
- **Biomarkers:**
  - 2024 tissue (NGS): EGFR L858R detected; T790M not detected; ALK, ROS1 and MET ex14 not detected; KRAS, BRAF, RET, NTRK and ERBB2 negative; PD-L1 TPS 5% (IHC).
  - 2025 ctDNA (liquid biopsy): L858R detected; T790M and C797S not detected; **MET amplification not assessable**.
- **Treatment Courses (lung, palliative systemic):** line 1 osimertinib (2024-02 → 2025-06, progression); line 2 carboplatin + pemetrexed (2025-07 → 2025-12, progression); line 3 docetaxel (2026-01 → last dose 2026-09-18, stopped for progression).
- **Treatment Courses (breast):** surgery 2017-03; adjuvant radiotherapy; adjuvant letrozole to 2022-04.
- **Imaging:**
  - CT 2026-10-02, progressive disease: chest wall nodule 9 → 13 → 17 mm; effusion 52 → 61 mm; primary 25 mm, stable.
  - MRI brain 2026-10-12: solitary 6 mm left frontal metastasis, no leptomeningeal disease.
- **CNS (2026-10-12/14):** present, 1 lesion, untreated, asymptomatic, not on regular steroids, no leptomeningeal disease.
- **Labs (2026-10-13):** Hb 104 L; neutrophils 3.9; platelets 241; creatinine 68; eGFR >90; bilirubin 9; ALT 22; AST 25; albumin 36.
- **Medications:** levothyroxine; ondansetron prn; dexamethasone as docetaxel premedication only; docetaxel (now stopped per plan).
- **Conditions:** hypothyroidism.
- **Management Plan:** verbatim from the 14/10/2026 letter.

## Gaps (must)
- **ECOG is not stated** (the letter only says "managing at home and walks daily"). It must be a gap, not inferred.
- MET amplification has not been tested on tissue.
- Brain metastasis stability: no prior imaging.

## Watch
- Dexamethasone is premedication around docetaxel, not regular steroid use. `on_steroids` should be false (or Unknown with that reason), not true.
- LVEF 60% (echo 2026-08) appears only in the letter.
- Other-malignancy windows count from the **2017 diagnosis** (~9.5 years) or from the **end of letrozole, 2022-04** (~4.5 years), depending on each trial's wording. A "5 years from completion of therapy" rule is **NOT_MET**; a "diagnosed within 5 years" rule is **MET**.
- Washout: last therapy is docetaxel, ending 2026-09-18.
- The target is the lung cancer, not the breast cancer.

## Expected matching behaviour
- **Trials requiring an EGFR mutation after osimertinib:** the driver criteria are MET; ECOG is **UNKNOWN**, so at best **Needs Information**.
- **Trials excluding untreated or unstable brain metastases:** NOT_MET or UNKNOWN depending on wording ("active", "untreated", "stable for ≥4 weeks").
- **Trials requiring ALK, ROS1, KRAS G12C or treatment-naive status:** EXCLUDED.
