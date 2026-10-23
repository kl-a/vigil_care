# Expected: Casey Fictional (synthetic)

## Clinical Record (must)
- **Cancer Diagnoses (2):**
  - NSCLC adenocarcinoma, left upper lobe, stage IVB, metastatic (adrenal, bone), active, dx 2025-10. The target.
  - Melanoma, left upper back, superficial spreading, pT2a pN0, stage IB, dx 2023-04, `no_evidence_of_disease`.
- **Biomarkers (2025-11, adrenal metastasis, NGS):**
  - KRAS G12C detected.
  - STK11 Q37* detected.
  - EGFR, BRAF, ERBB2, MET ex14, ALK, ROS1, RET and NTRK negative.
  - PD-L1 TPS 30%.
- **Treatment Courses:**
  - Line 1: carboplatin + pemetrexed + pembrolizumab (2025-11-20 → 2026-08-06). Best response: partial response (responding). Stopped for progression.
  - Radiotherapy to L2, 8 Gy, 2026-09-22 (palliative).
  - Melanoma: wide excision + SLNB, 2023-04 (curative surgery).
- **Imaging:** CT 2026-10-01, progressive disease. Primary 41 mm; L adrenal 36 mm; new R adrenal 14 mm; new L2 lytic lesion 22 mm.
- **CNS (2026-09-29, from the letter):** no brain metastases.
- **ECOG:** 2 (2026-10-08).
- **Labs (2026-10-06):** creatinine 126 H; eGFR 49 L; albumin 31 L; ALP 162 H; Hb 118 L; HbA1c 7.4 H; neutrophils 6.8; platelets 388.
- **Conditions:** CKD 3a; T2DM; COPD.
- **Medications:** metformin; empagliflozin; tiotropium; oxycodone CR and prn; denosumab.

## Watch
- The adrenal histopathology explicitly says **not melanoma**: the adrenal disease belongs to the lung cancer.
- Prior **immunotherapy**: pembrolizumab. Prior **KRAS G12C inhibitor**: none.
- Washout: last systemic therapy ended 2026-08-06 (over 60 days before the run). Palliative radiotherapy was 2026-09-22; some trials have a separate radiotherapy washout (often 7–14 days).
- Creatinine clearance isn't reported. Cockcroft-Gault needs weight, so CrCl criteria are **UNKNOWN** unless the trial accepts eGFR.

## Expected matching behaviour
- **Trials requiring ECOG 0–1:** EXCLUDED on ECOG.
- **"No other malignancy within 5 (or 3) years":** NOT_MET. The melanoma was 2023-04, about 3.5 years ago, so EXCLUDED, citing the melanoma Cancer Diagnosis. A rule allowing "adequately treated, no evidence of disease" may be MET; the rationale must say which wording applied.
- **KRAS G12C trials allowing ECOG 2 and permitting prior melanoma:** NEEDS_INFORMATION at best (renal function).
