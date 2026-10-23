"""Helpers for the synthetic Patients' documents as HTML . All people, numbers and organisations are fictional."""
import os
from textwrap import dedent

ONC = ("Southside Oncology (synthetic)", "Suite 4, 10 Example Ave, Kogarah NSW 2217<br>Ph 02 9000 0000 · Fax 02 9000 0001")
RAD = ("Harbour Example Radiology", "1 Sample St, Sydney NSW 2000<br>Ph 02 9000 1000 · ABN 00 000 000 000")
PATH = ("Synthetic Pathology Pty Ltd", "Level 2, 5 Placeholder Rd, Macquarie Park NSW 2113<br>NATA Accreditation 0000 · Ph 1300 000 000")
GENO = ("Example Genomics Laboratory", "8 Fictional Way, Camperdown NSW 2050<br>NATA Accreditation 0001")

def page(org, title, body):
    return dedent(f"""\
    <!doctype html><html><head><meta charset="utf-8"><title>{title}</title><link rel="stylesheet" href="../../style.css"></head><body>
    <div class="synthetic">SYNTHETIC TEST DOCUMENT · FICTIONAL PATIENT · NOT A REAL MEDICAL RECORD</div>
    <div class="lh"><div class="org">{org[0]}</div><div class="addr">{org[1]}</div></div>
    """) + dedent(body) + "\n</body></html>\n"

def pt(name, dob, mrn, extra=""):
    return f'<table class="pt"><tr><td><b>Patient:</b></td><td>{name}</td><td><b>DOB:</b></td><td>{dob}</td></tr><tr><td><b>MRN:</b></td><td>{mrn}</td>{extra}</tr></table>'

def labs(rows):
    out = ['<table class="res"><tr><th>Test</th><th>Result</th><th>Units</th><th>Reference range</th><th></th></tr>']
    for r in rows:
        test, val, unit, rng, flag = (list(r) + [""])[:5]
        out.append(f'<tr><td>{test}</td><td class="{"f" if flag else ""}">{val}</td><td>{unit}</td><td>{rng}</td><td class="f">{flag}</td></tr>')
    return "\n".join(out) + "</table>"

DOCS = {}
def doc(patient, fname, org, title, body):
    DOCS[(patient, fname)] = page(org, title, body)

