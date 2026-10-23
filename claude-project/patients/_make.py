"""Writes the synthetic Patients' documents as HTML; render.sh turns them into PDFs. All people, numbers and organisations are fictional."""
import os

import p1_docs, p2_docs, p3_docs  # noqa: F401  (each registers its documents)
from docs_lib import DOCS

for (patient, fname), html in DOCS.items():
    os.makedirs(f"{patient}/src", exist_ok=True)
    with open(f"{patient}/src/{fname}.html", "w") as f:
        f.write(html)
print(len(DOCS), "documents written")
