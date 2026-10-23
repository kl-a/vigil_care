"""Patient 1: Dana Example. EGFR L858R lung adenocarcinoma, post-osimertinib, three lines, a new small brain metastasis. Shaped like the example briefing."""
from docs_lib import GENO, ONC, PATH, RAD, doc, labs, pt

P = "p1-dana-example"
NAME, DOB, MRN = "Dana EXAMPLE", "14/05/1962", "SO-100451"

doc(P, "2024-01-19_histopathology_bronchoscopic-biopsy", PATH, "Histopathology report", f"""
<h1>HISTOPATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>MP-24-000731</td>')}
<p><b>Requesting doctor:</b> Dr Alex Rivera (synthetic) · <b>Collected:</b> 16/01/2024 · <b>Reported:</b> 19/01/2024</p>
<h2>Specimen</h2><p>Right upper lobe, endobronchial biopsy (x4 fragments).</p>
<h2>Microscopy</h2>
<p>Fragments of bronchial mucosa infiltrated by a moderately differentiated adenocarcinoma with acinar and lepidic growth patterns. No squamous or neuroendocrine morphology.</p>
<h2>Immunohistochemistry</h2>
<p>TTF-1: positive. Napsin A: positive. CK7: positive. CK20: negative. p40: negative. Synaptophysin: negative.</p>
<h2>Diagnosis</h2>
<p><b>Right upper lobe biopsy: adenocarcinoma, consistent with primary lung origin (TTF-1+, Napsin A+, CK7+).</b></p>
<p>Tissue sufficient for molecular testing. Block A1 referred to Example Genomics Laboratory for NGS panel and PD-L1.</p>
<p class="sig">Dr R. Fictitious, Anatomical Pathologist</p>
""")

doc(P, "2024-02-02_molecular_ngs-and-pdl1", GENO, "Molecular pathology report", f"""
<h1>MOLECULAR PATHOLOGY REPORT: NSCLC NGS PANEL</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>GX-24-01177</td>')}
<p><b>Specimen:</b> MP-24-000731 block A1, right upper lobe biopsy (primary) · <b>Tumour content:</b> ~40% · <b>Reported:</b> 02/02/2024</p>
<h2>Results</h2>
<table class="res"><tr><th>Gene</th><th>Method</th><th>Result</th></tr>
<tr><td>EGFR</td><td>NGS</td><td class="f">c.2573T&gt;G p.(Leu858Arg), exon 21 (L858R) DETECTED, VAF 31%</td></tr>
<tr><td>EGFR T790M</td><td>NGS</td><td>Not detected</td></tr>
<tr><td>ALK</td><td>NGS (RNA fusion)</td><td>No fusion detected</td></tr>
<tr><td>ROS1</td><td>NGS (RNA fusion)</td><td>No fusion detected</td></tr>
<tr><td>MET exon 14 skipping</td><td>NGS (RNA)</td><td>Not detected</td></tr>
<tr><td>KRAS, BRAF, RET, NTRK1-3, ERBB2</td><td>NGS</td><td>No pathogenic variants detected</td></tr>
<tr><td>PD-L1 (22C3)</td><td>IHC</td><td>Tumour Proportion Score 5%</td></tr>
</table>
<p><b>Interpretation:</b> EGFR exon 21 L858R sensitising mutation. Eligible for PBS-subsidised EGFR TKI therapy. MET amplification is not reported by this panel.</p>
<p class="sig">Dr J. Placeholder, Molecular Pathologist</p>
""")

doc(P, "2025-07-08_molecular_ctdna-liquid-biopsy", GENO, "Liquid biopsy report", f"""
<h1>CIRCULATING TUMOUR DNA (ctDNA) REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>GX-25-08802</td>')}
<p><b>Specimen:</b> Plasma (liquid biopsy), collected 30/06/2025 · <b>Reported:</b> 08/07/2025 · <b>Clinical note:</b> progression on osimertinib</p>
<table class="res"><tr><th>Gene</th><th>Result</th></tr>
<tr><td>EGFR L858R</td><td class="f">Detected (VAF 4.2%)</td></tr>
<tr><td>EGFR T790M</td><td>Not detected</td></tr>
<tr><td>EGFR C797S</td><td>Not detected</td></tr>
<tr><td>MET amplification</td><td>Not assessable by this assay (copy number not reported)</td></tr>
</table>
<p><b>Comment:</b> No on-target EGFR resistance mutation identified. Off-target mechanisms (e.g. MET amplification, histological transformation) cannot be excluded; tissue re-biopsy may be considered.</p>
<p class="sig">Dr J. Placeholder, Molecular Pathologist</p>
""")

doc(P, "2026-10-02_radiology_ct-chest-abdomen-pelvis", RAD, "CT report", f"""
<h1>CT CHEST, ABDOMEN AND PELVIS WITH CONTRAST</h1>
{pt(NAME, DOB, MRN, '<td><b>Accession:</b></td><td>HX-26-55120</td>')}
<p><b>Date of examination:</b> 02/10/2026 · <b>Referrer:</b> Dr Alex Rivera (synthetic)</p>
<p><b>Clinical details:</b> Metastatic EGFR-mutant lung adenocarcinoma on docetaxel. Restaging.</p>
<p><b>Comparison:</b> CT 03/07/2026 and 02/04/2026.</p>
<h2>Findings</h2>
<p>Right upper lobe primary mass measures 25 x 21 mm (previously 24 x 21 mm), stable.</p>
<p>Extensive right pleural thickening and nodularity, unchanged. Loculated right pleural effusion, maximal depth 61 mm (previously 52 mm), mildly increased.</p>
<p>Right lateral chest wall soft tissue nodule at the level of the 6th rib measures 17 mm (previously 13 mm in July and 9 mm in April), progressively enlarging.</p>
<p>Sclerotic lesions in the right 6th rib and T12 vertebral body are unchanged.</p>
<p>No new pulmonary nodules. No interstitial lung disease. Liver, adrenals and abdominal nodes normal. No ascites.</p>
<h2>Impression</h2>
<p><b>1. Mixed response: stable primary; progressive right chest wall nodule (17 mm, from 13 mm) and mildly increased loculated right pleural effusion. Overall appearances in keeping with progressive disease.</b><br>
2. Stable sclerotic bone lesions (right 6th rib, T12).</p>
<p class="sig">Dr K. Example, Radiologist</p>
""")

doc(P, "2026-10-12_radiology_mri-brain", RAD, "MRI report", f"""
<h1>MRI BRAIN WITH GADOLINIUM</h1>
{pt(NAME, DOB, MRN, '<td><b>Accession:</b></td><td>HX-26-57004</td>')}
<p><b>Date of examination:</b> 12/10/2026 · <b>Referrer:</b> Dr Alex Rivera (synthetic)</p>
<p><b>Clinical details:</b> Metastatic lung adenocarcinoma. Staging. No neurological symptoms.</p>
<p><b>Comparison:</b> None available.</p>
<h2>Findings</h2>
<p>A single 6 mm enhancing lesion in the left frontal lobe at the grey-white junction with minimal surrounding vasogenic oedema. No mass effect or midline shift.</p>
<p>No other enhancing lesions. No leptomeningeal enhancement. Ventricles and extra-axial spaces normal.</p>
<h2>Impression</h2>
<p><b>Solitary 6 mm left frontal enhancing lesion, consistent with a cerebral metastasis. No leptomeningeal disease.</b> No prior imaging for comparison.</p>
<p class="sig">Dr K. Example, Radiologist</p>
""")

doc(P, "2026-10-13_bloods_fbc-eluc-lft", PATH, "Blood results", f"""
<h1>CUMULATIVE PATHOLOGY REPORT</h1>
{pt(NAME, DOB, MRN, '<td><b>Lab no:</b></td><td>26-4410093</td>')}
<p><b>Collected:</b> 13/10/2026 08:20 · <b>Requesting doctor:</b> Dr Alex Rivera (synthetic)</p>
<h2>Full blood count</h2>
{labs([("Haemoglobin","104","g/L","115–165","L"),("White cell count","5.8","x10^9/L","4.0–11.0"),("Neutrophils","3.9","x10^9/L","2.0–7.5"),("Platelets","241","x10^9/L","150–400")])}
<h2>Electrolytes, urea, creatinine</h2>
{labs([("Sodium","138","mmol/L","135–145"),("Potassium","4.2","mmol/L","3.5–5.2"),("Creatinine","68","umol/L","45–90"),("eGFR","&gt;90","mL/min/1.73m2","&gt;59")])}
<h2>Liver function tests</h2>
{labs([("Bilirubin","9","umol/L","&lt;20"),("ALT","22","U/L","&lt;34"),("AST","25","U/L","&lt;35"),("ALP","98","U/L","30–110"),("Albumin","36","g/L","35–50")])}
<p class="small">Comment: mild normocytic anaemia.</p>
""")

doc(P, "2026-10-14_letter_medical-oncology", ONC, "Clinic letter", f"""
<p>14 October 2026</p>
<p>Dr Morgan Grey (synthetic)<br>Example Family Practice<br>22 Sample Pde, Hurstville NSW 2220</p>
<p>Dear Morgan,</p>
<p><b>Re: Dana EXAMPLE, DOB 14/05/1962, 9 Placeholder St, Hurstville NSW 2220</b></p>
<p><b>Diagnosis:</b> Stage IV EGFR-mutant (exon 21 L858R) adenocarcinoma of the right upper lobe, diagnosed January 2024 (TTF-1+, Napsin A+). Initial staging showed right pleural disease and rib/T12 bone metastases.</p>
<p><b>Past history:</b><br>
- Left breast cancer 2017: invasive ductal carcinoma, T1N0, ER/PR positive, HER2 negative. Wide local excision and sentinel node biopsy (March 2017), adjuvant radiotherapy, and letrozole for 5 years (completed April 2022). No evidence of recurrence.<br>
- Hypothyroidism.</p>
<p><b>Treatment to date:</b><br>
1. Osimertinib 80 mg daily, February 2024 to June 2025: partial response, then progression (chest wall and pleura).<br>
2. Carboplatin and pemetrexed, July 2025 to December 2025 (6 cycles, then pemetrexed maintenance stopped at progression in December 2025).<br>
3. Docetaxel 75 mg/m2 three-weekly, January 2026 to present; last cycle 18 September 2026.</p>
<p><b>Medications:</b> Docetaxel as above; levothyroxine 100 mcg daily; dexamethasone 8 mg on the day before, of and after each docetaxel cycle only (premedication); ondansetron 8 mg prn.</p>
<p>I reviewed Dana today with the restaging CT of 2 October and the MRI brain of 12 October. The CT shows progressive disease: the right chest wall nodule has grown from 13 to 17 mm and the loculated right effusion is slightly larger. Her last pleural tap was in March 2026 and she is not breathless at rest. The MRI shows a new solitary 6 mm left frontal metastasis. She has no headaches, focal weakness or seizures and is not on regular steroids.</p>
<p>She is managing at home and walks daily, although she tires easily after docetaxel. Haemoglobin is 104 g/L; renal and liver function are normal. An echocardiogram in August 2026 showed an LVEF of 60%.</p>
<p>We discussed that docetaxel is no longer controlling her disease. Archival tissue from January 2024 (MP-24-000731) is available; a repeat biopsy of the chest wall nodule could clarify the resistance mechanism, and she would accept this.</p>
<p><b>Plan:</b><br>
1. Stop docetaxel.<br>
2. Discuss at the thoracic MDT on 21 October regarding stereotactic radiosurgery to the brain lesion versus surveillance MRI in 4 weeks.<br>
3. Explore clinical trial options for EGFR-mutant NSCLC after osimertinib, including antibody-drug conjugates.<br>
4. Consider core biopsy of the chest wall nodule for tissue NGS including MET amplification.<br>
5. Review in 2 weeks.</p>
<p>Kind regards,</p>
<p class="sig">Dr Alex Rivera (synthetic)<br>Medical Oncologist</p>
""")
