"""Patient 2: Jordan Placeholder. ALK-positive lung adenocarcinoma, stage IVA, treatment-naive, ECOG 1, no brain metastases."""
from docs_lib import GENO, ONC, PATH, RAD, doc, labs, pt

P = "p2-jordan-placeholder"
NAME, DOB, MRN = "Jordan PLACEHOLDER", "30/08/1979", "SO-100587"
GP = ("Parramatta Example Medical Centre", "40 Fictional St, Parramatta NSW 2150<br>Ph 02 9000 2000 · Fax 02 9000 2001")

doc(P, "2026-09-02_letter_gp-referral", GP, "GP referral", f"""
<p>2 September 2026</p>
<p>Dr Alex Rivera (synthetic)<br>Southside Oncology, Kogarah NSW 2217</p>
<p>Dear Dr Rivera,</p>
<p><b>Re: Jordan PLACEHOLDER, DOB 30/08/1979, 3 Sample Lane, Parramatta NSW 2150. Medicare 0000 00000 0 (synthetic)</b></p>
<p>Thank you for seeing Jordan, a 47-year-old software engineer and lifelong non-smoker, with a 3-month history of dry cough and right-sided chest discomfort. A CT chest on 28 August showed a right lower lobe mass with mediastinal lymphadenopathy and a contralateral lung nodule. I have arranged a PET scan and respiratory referral for EBUS.</p>
<p><b>Past history:</b> Hypertension (2019). Mild asthma since childhood. Appendicectomy 1995.</p>
<p><b>Current medications:</b> Perindopril 5 mg daily. Salbutamol 100 mcg inhaler 2 puffs prn.</p>
<p><b>Allergies:</b> Nil known.</p>
<p><b>Social:</b> Married, two children. Works full time. Never smoked. Alcohol 4 standard drinks per week.</p>
<p>Many thanks for your assistance.</p>
<p class="sig">Dr Sam Example (synthetic)<br>General Practitioner</p>
""")

doc(P, "2026-08-28_radiology_ct-chest", RAD, "CT report", f"""
<h1>CT CHEST WITH CONTRAST</h1>
{pt(NAME, DOB, MRN, '<td><b>Accession:</b></td><td>HX-26-48812</td>')}
<p><b>Date of examination:</b> 28/08/2026 · <b>Referrer:</b> Dr Sam Example (synthetic)</p>
<p><b>Clinical details:</b> Persistent cough, right chest pain. Non-smoker.</p>
<h2>Findings</h2>
<p>Right lower lobe spiculated mass, 38 x 31 mm. Enlarged right hilar (14 mm short axis) and subcarinal (18 mm short axis) lymph nodes.</p>
<p>Left lower lobe solid nodule, 9 mm, suspicious for metastasis. Small right pleural effusion, no pleural nodularity.</p>
<p>Upper abdomen: no adrenal or liver lesion.</p>
<h2>Impression</h2>
<p><b>Right lower lobe mass with right hilar and subcarinal adenopathy and a 9 mm contralateral left lower lobe nodule, suspicious for primary lung malignancy with contralateral pulmonary metastasis.</b></p>
<p class="sig">Dr K. Example, Radiologist</p>
""")

doc(P, "2026-09-10_radiology_pet-ct", RAD, "PET-CT report", f"""
<h1>FDG PET-CT (SKULL BASE TO MID-THIGH)</h1>
{pt(NAME, DOB, MRN, '<td><b>Accession:</b></td><td>HX-26-50377</td>')}
<p><b>Date of examination:</b> 10/09/2026 · <b>Comparison:</b> CT chest 28/08/2026</p>
<h2>Findings</h2>
<p>Right lower lobe mass, 38 mm, SUVmax 11.2. Right hilar (SUVmax 7.1) and subcarinal (SUVmax 8.4) nodes avid.</p>
<p>Left lower lobe 9 mm nodule, SUVmax 3.0 (avid relative to size).</p>
<p>No avid supraclavicular, abdominal or skeletal disease. Small right effusion without avidity.</p>
<h2>Impression</h2>
<p><b>Avid right lower lobe primary with N2 nodal disease and a contralateral lung metastasis (M1a). No extrathoracic disease.</b></p>
<p class="sig">Dr P. Sample, Nuclear Medicine Physician</p>
""")

doc(P, "2026-09-15_histopathology_ebus-tbna", PATH, "Histopathology report", f"""
<h1>CYTOPATHOLOGY / HISTOPATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>MP-26-021408</td>')}
<p><b>Collected:</b> 12/09/2026 · <b>Reported:</b> 15/09/2026 · <b>Requesting doctor:</b> Dr L. Fictional, Respiratory Physician</p>
<h2>Specimen</h2><p>EBUS-TBNA, station 7 (subcarinal) lymph node, with cell block.</p>
<h2>Microscopy and immunohistochemistry</h2>
<p>Cell block shows metastatic adenocarcinoma with solid and signet-ring features. TTF-1 positive, Napsin A positive, CK7 positive, p40 negative. ALK (D5F3) immunohistochemistry: <b>strongly positive</b>.</p>
<h2>Diagnosis</h2>
<p><b>Station 7 lymph node: metastatic adenocarcinoma of lung origin. ALK IHC positive.</b> Material forwarded for NGS confirmation and PD-L1.</p>
<p class="sig">Dr R. Fictitious, Anatomical Pathologist</p>
""")

doc(P, "2026-09-22_molecular_ngs", GENO, "Molecular pathology report", f"""
<h1>MOLECULAR PATHOLOGY REPORT: NSCLC NGS PANEL</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>GX-26-10954</td>')}
<p><b>Specimen:</b> MP-26-021408, station 7 lymph node (metastasis) · <b>Reported:</b> 22/09/2026</p>
<table class="res"><tr><th>Gene</th><th>Method</th><th>Result</th></tr>
<tr><td>ALK</td><td>NGS (RNA fusion)</td><td class="f">EML4-ALK fusion (variant 3, E6:A20) DETECTED</td></tr>
<tr><td>EGFR</td><td>NGS</td><td>No pathogenic variant detected</td></tr>
<tr><td>ROS1, RET, NTRK1-3</td><td>NGS (RNA fusion)</td><td>No fusion detected</td></tr>
<tr><td>KRAS, BRAF, ERBB2, MET exon 14</td><td>NGS</td><td>No pathogenic variant detected</td></tr>
<tr><td>TP53</td><td>NGS</td><td>c.743G&gt;A p.(Arg248Gln) detected, VAF 22%</td></tr>
<tr><td>PD-L1 (22C3)</td><td>IHC</td><td>Tumour Proportion Score 60%</td></tr>
</table>
<p><b>Interpretation:</b> EML4-ALK fusion confirmed (variant 3). Co-occurring TP53 mutation.</p>
<p class="sig">Dr J. Placeholder, Molecular Pathologist</p>
""")

doc(P, "2026-09-24_bloods_fbc-eluc-lft", PATH, "Blood results", f"""
<h1>PATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>26-3982215</td>')}
<p><b>Collected:</b> 24/09/2026 07:45</p>
<h2>Full blood count</h2>
{labs([("Haemoglobin","142","g/L","130–180"),("White cell count","7.9","x10^9/L","4.0–11.0"),("Neutrophils","5.1","x10^9/L","2.0–7.5"),("Platelets","312","x10^9/L","150–400")])}
<h2>Electrolytes, urea, creatinine</h2>
{labs([("Creatinine","84","umol/L","60–110"),("eGFR","88","mL/min/1.73m2","&gt;59")])}
<h2>Liver function tests</h2>
{labs([("Bilirubin","12","umol/L","&lt;20"),("ALT","61","U/L","&lt;45","H"),("AST","38","U/L","&lt;35","H"),("ALP","104","U/L","30–110"),("Albumin","41","g/L","35–50")])}
<h2>Other</h2>
{labs([("CEA","8.6","ug/L","&lt;5.0","H"),("Total cholesterol","5.9","mmol/L","&lt;5.5","H")])}
""")

doc(P, "2026-09-26_letter_medical-oncology", ONC, "Clinic letter", f"""
<p>26 September 2026</p>
<p>Dr Sam Example (synthetic)<br>Parramatta Example Medical Centre</p>
<p>Dear Sam,</p>
<p><b>Re: Jordan PLACEHOLDER, DOB 30/08/1979</b></p>
<p><b>Diagnosis:</b> Stage IVA (cT2bN2M1a) ALK-rearranged (EML4-ALK variant 3) adenocarcinoma of the right lower lobe, with a contralateral left lower lobe metastasis. PD-L1 TPS 60%. MRI brain 23/09/2026: no intracranial metastases.</p>
<p>Thank you for referring Jordan. He remains fully active and working, with a mild cough only. <b>ECOG performance status 1.</b> Examination was unremarkable.</p>
<p>Bloods show mildly raised ALT (61) and AST (38), likely related to moderate alcohol intake or fatty liver; bilirubin is normal. Renal function is normal.</p>
<p>No treatment has yet been given for his lung cancer.</p>
<p><b>Plan:</b><br>
1. First-line ALK inhibitor: alectinib 600 mg twice daily (PBS) or lorlatinib, discussed today; Jordan would like to consider clinical trials first.<br>
2. Screen for first-line ALK-positive NSCLC trials before starting treatment, within the next 2 weeks.<br>
3. Repeat LFTs in 1 week.<br>
4. Review 3 October 2026.</p>
<p>Kind regards,</p>
<p class="sig">Dr Alex Rivera (synthetic)<br>Medical Oncologist</p>
""")
