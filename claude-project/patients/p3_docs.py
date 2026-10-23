"""Patient 3: Casey Fictional. KRAS G12C lung adenocarcinoma after first-line chemo-immunotherapy, ECOG 2, prior melanoma (2023), CKD 3a. Tests the other-malignancy exclusion and organ function."""
from docs_lib import GENO, ONC, PATH, RAD, doc, labs, pt

P = "p3-casey-fictional"
NAME, DOB, MRN = "Casey FICTIONAL", "03/02/1951", "SO-100219"
DERM = ("Illawarra Example Skin Pathology", "12 Sample Rd, Wollongong NSW 2500<br>NATA Accreditation 0002")

doc(P, "2023-04-20_histopathology_melanoma-excision", DERM, "Histopathology report", f"""
<h1>HISTOPATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>IS-23-004417</td>')}
<p><b>Collected:</b> 14/04/2023 · <b>Reported:</b> 20/04/2023 · <b>Specimen:</b> Skin, left upper back, wide excision</p>
<h2>Diagnosis</h2>
<p><b>Invasive superficial spreading melanoma, left upper back.</b><br>
Breslow thickness 1.4 mm. Clark level IV. No ulceration. Mitoses 2/mm2. No lymphovascular or perineural invasion. Margins clear (closest peripheral 8 mm, deep 4 mm).<br>
Sentinel lymph node biopsy (left axilla): 0/2 nodes involved.</p>
<p><b>Pathological stage (AJCC 8th): pT2a pN0 (stage IB).</b></p>
<p class="sig">Dr M. Example, Dermatopathologist</p>
""")

doc(P, "2025-10-30_histopathology_ct-guided-adrenal-biopsy", PATH, "Histopathology report", f"""
<h1>HISTOPATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>MP-25-030912</td>')}
<p><b>Collected:</b> 27/10/2025 · <b>Reported:</b> 30/10/2025 · <b>Specimen:</b> CT-guided core biopsy, left adrenal mass</p>
<h2>Microscopy</h2>
<p>Cores of adrenal tissue infiltrated by poorly differentiated adenocarcinoma. TTF-1 positive, Napsin A positive, CK7 positive. SOX10 negative, Melan-A negative, S100 negative (melanoma excluded).</p>
<h2>Diagnosis</h2>
<p><b>Left adrenal: metastatic adenocarcinoma of lung origin. Not melanoma.</b></p>
<p class="sig">Dr R. Fictitious, Anatomical Pathologist</p>
""")

doc(P, "2025-11-12_molecular_ngs", GENO, "Molecular pathology report", f"""
<h1>MOLECULAR PATHOLOGY REPORT: NSCLC NGS PANEL</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>GX-25-14420</td>')}
<p><b>Specimen:</b> MP-25-030912, left adrenal (metastasis) · <b>Reported:</b> 12/11/2025</p>
<table class="res"><tr><th>Gene</th><th>Method</th><th>Result</th></tr>
<tr><td>KRAS</td><td>NGS</td><td class="f">c.34G&gt;T p.(Gly12Cys) (G12C) DETECTED, VAF 27%</td></tr>
<tr><td>STK11</td><td>NGS</td><td>c.109C&gt;T p.(Gln37*) detected, VAF 25%</td></tr>
<tr><td>EGFR, BRAF, ERBB2, MET exon 14</td><td>NGS</td><td>No pathogenic variant detected</td></tr>
<tr><td>ALK, ROS1, RET, NTRK1-3</td><td>NGS (RNA fusion)</td><td>No fusion detected</td></tr>
<tr><td>PD-L1 (22C3)</td><td>IHC</td><td>Tumour Proportion Score 30%</td></tr>
</table>
<p class="sig">Dr J. Placeholder, Molecular Pathologist</p>
""")

doc(P, "2026-10-01_radiology_ct-chest-abdomen-pelvis", RAD, "CT report", f"""
<h1>CT CHEST, ABDOMEN AND PELVIS WITH CONTRAST</h1>
{pt(NAME, DOB, MRN, '<td><b>Accession:</b></td><td>HX-26-55010</td>')}
<p><b>Date of examination:</b> 01/10/2026 · <b>Comparison:</b> CT 02/07/2026</p>
<p><b>Clinical details:</b> Metastatic KRAS G12C NSCLC. Completed carboplatin/pemetrexed/pembrolizumab, now off treatment. Restaging.</p>
<h2>Findings</h2>
<p>Left upper lobe primary mass 41 x 35 mm (previously 33 x 30 mm).</p>
<p>Left adrenal metastasis 36 mm (previously 28 mm). New right adrenal nodule 14 mm.</p>
<p>Lytic lesion in the L2 vertebral body with a soft tissue component, 22 mm, new since July; no canal compromise. Previously noted left iliac sclerotic lesion unchanged.</p>
<p>Moderate centrilobular and paraseptal emphysema. No pneumonitis. Liver clear.</p>
<h2>Impression</h2>
<p><b>Progressive disease: enlarging left upper lobe primary and left adrenal metastasis; new right adrenal nodule and new L2 lytic metastasis.</b></p>
<p class="sig">Dr K. Example, Radiologist</p>
""")

doc(P, "2026-10-06_bloods_fbc-eluc-lft", PATH, "Blood results", f"""
<h1>PATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>26-4371120</td>')}
<p><b>Collected:</b> 06/10/2026 09:10</p>
<h2>Full blood count</h2>
{labs([("Haemoglobin","118","g/L","130–180","L"),("White cell count","9.4","x10^9/L","4.0–11.0"),("Neutrophils","6.8","x10^9/L","2.0–7.5"),("Platelets","388","x10^9/L","150–400")])}
<h2>Electrolytes, urea, creatinine</h2>
{labs([("Sodium","136","mmol/L","135–145"),("Creatinine","126","umol/L","60–110","H"),("eGFR","49","mL/min/1.73m2","&gt;59","L"),("Corrected calcium","2.48","mmol/L","2.10–2.60")])}
<h2>Liver function tests</h2>
{labs([("Bilirubin","11","umol/L","&lt;20"),("ALT","28","U/L","&lt;45"),("AST","31","U/L","&lt;35"),("ALP","162","U/L","30–110","H"),("Albumin","31","g/L","35–50","L")])}
<h2>Diabetes</h2>
{labs([("HbA1c","7.4","%","&lt;6.5","H")])}
""")

doc(P, "2026-10-08_letter_medical-oncology", ONC, "Clinic letter", f"""
<p>8 October 2026</p>
<p>Dr Morgan Grey (synthetic)<br>Example Family Practice</p>
<p>Dear Morgan,</p>
<p><b>Re: Casey FICTIONAL, DOB 03/02/1951, 18 Example Cres, Wollongong NSW 2500</b></p>
<p><b>Diagnosis:</b> Stage IVB KRAS G12C-mutant adenocarcinoma of the left upper lobe (diagnosed October 2025), with adrenal and bone metastases. STK11 co-mutation. PD-L1 TPS 30%.</p>
<p><b>Other history:</b><br>
- Melanoma, left upper back, stage IB (pT2a pN0), wide excision and sentinel node biopsy April 2023. Under dermatology surveillance, no recurrence.<br>
- Chronic kidney disease stage 3a (eGFR 45–55).<br>
- Type 2 diabetes mellitus.<br>
- COPD (ex-smoker, 40 pack-years, quit 2015).</p>
<p><b>Treatment to date:</b><br>
1. Carboplatin AUC 5, pemetrexed and pembrolizumab, 4 cycles from 20 November 2025, then pemetrexed and pembrolizumab maintenance until 6 August 2026 (last dose). Best response partial response (CT February 2026). Pembrolizumab stopped for progression; no immune-related adverse events.</p>
<p><b>Medications:</b> Metformin 1 g twice daily; empagliflozin 10 mg daily; tiotropium 18 mcg inhaled daily; oxycodone CR 10 mg twice daily and oxycodone 5 mg prn for L2 back pain; denosumab 120 mg subcut every 4 weeks (started September 2026).</p>
<p>Casey has had a difficult two months with back pain from the new L2 lesion and reduced appetite. He is up and about more than half the day and manages self-care, but no longer drives or does the garden. <b>ECOG 2.</b> MRI brain on 29 September 2026 showed no intracranial metastases. Radiotherapy to L2 (8 Gy single fraction) was given on 22 September 2026 with improvement in pain.</p>
<p>The CT of 1 October confirms progressive disease. Creatinine is 126 with eGFR 49, and albumin is 31.</p>
<p><b>Plan:</b><br>
1. Second-line options discussed: sotorasib (KRAS G12C inhibitor, PBS) or docetaxel; also clinical trials of KRAS G12C inhibitors, noting his ECOG of 2 and prior melanoma.<br>
2. Trial screening this week; if no suitable trial, start sotorasib 960 mg daily.<br>
3. Review 15 October 2026.</p>
<p>Kind regards,</p>
<p class="sig">Dr Alex Rivera (synthetic)<br>Medical Oncologist</p>
""")
