# Expected: Jordan Placeholder (synthetic)

## Clinical Record (must)
- **Cancer Diagnosis:** NSCLC adenocarcinoma, right lower lobe, stage IVA (cT2bN2M1a), metastatic, active, dx 2026-09. The target.
- **Biomarkers (2026-09):**
  - ALK positive by IHC (D5F3).
  - EML4-ALK fusion variant 3 by NGS (metastasis specimen).
  - EGFR, ROS1, RET, NTRK, KRAS, BRAF, ERBB2 and MET ex14 negative.
  - TP53 R248Q detected.
  - PD-L1 TPS 60%.
- **Treatment Courses:** none for the cancer (treatment-naive). Prior systemic lines = 0.
- **Imaging:**
  - CT 2026-08-28.
  - PET-CT 2026-09-10: primary 38 mm, SUVmax 11.2; N2; contralateral 9 mm nodule; no extrathoracic disease.
  - Measurable disease: present (38 mm primary).
- **CNS (2026-09-23, from the letter):** no brain metastases.
- **ECOG:** 1 (2026-09-26).
- **Labs (2026-09-24):** ALT 61 H; AST 38 H; bilirubin 12; creatinine 84; eGFR 88; Hb 142; CEA 8.6 H.
- **Conditions:** hypertension; asthma (appendicectomy is history).
- **Medications:** perindopril; salbutamol prn.
- **Management Plan:** verbatim from the 26/09/2026 letter.

## Watch
- The GP referral **predates** the diagnosis; don't take its "suspicious" wording as the diagnosis.
- The MRI brain is mentioned only in the letter; there's no MRI report. The CNS fact must quote the letter.
- ALT 61 is about 1.4× ULN, which passes the usual "≤2.5× ULN" organ-function criteria (MET); state the multiple.
- No other malignancy.

## Expected matching behaviour
- **First-line ALK+ trials:** mostly POTENTIALLY_ELIGIBLE, or NEEDS_INFORMATION for things like LVEF or QTc that the documents don't give.
- **Trials requiring prior ALK TKI or prior therapy:** EXCLUDED (no prior lines).
- **EGFR- or KRAS-driven trials:** EXCLUDED.
