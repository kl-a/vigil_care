"""Cancer Types keyed to MeSH (#37): each Cancer Type carries its MeSH term and ID, so our terms match the
trial registries' conditions (ClinicalTrials.gov maps conditions to MeSH). Seeds the shortlist; the full MeSH
Neoplasms list is kept in app/specialties/oncology/data/mesh_neoplasms.json (revisit-later #28). Every MeSH ID
here was checked against NLM's MeSH lookup on 2026-09-27.

Design doc §6.3.

Revision ID: 0012_cancer_types_mesh
Revises: 0011_lab_panels
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_cancer_types_mesh"
down_revision = "0011_lab_panels"
branch_labels = None
depends_on = None

TNM = ["TNM"]
FIGO = ["FIGO"]
# (key, display name, MeSH term, MeSH ID, staging systems)
SHORTLIST = [
    ("breast", "Breast cancer", "Breast Neoplasms", "D001943", TNM),
    ("nsclc", "Non-small cell lung cancer", "Carcinoma, Non-Small-Cell Lung", "D002289", TNM),
    ("sclc", "Small cell lung cancer", "Small Cell Lung Carcinoma", "D055752", TNM),
    ("mesothelioma", "Mesothelioma", "Mesothelioma, Malignant", "D000086002", TNM),
    ("colorectal", "Colorectal cancer", "Colorectal Neoplasms", "D015179", TNM),
    ("anal", "Anal cancer", "Anus Neoplasms", "D001005", TNM),
    ("gastric", "Gastric cancer", "Stomach Neoplasms", "D013274", TNM),
    ("oesophageal", "Oesophageal cancer", "Esophageal Neoplasms", "D004938", TNM),
    ("pancreatic", "Pancreatic cancer", "Pancreatic Neoplasms", "D010190", TNM),
    ("hepatocellular", "Hepatocellular carcinoma", "Carcinoma, Hepatocellular", "D006528", ["TNM", "BCLC"]),
    ("biliary", "Biliary tract cancer", "Biliary Tract Neoplasms", "D001661", TNM),
    ("prostate", "Prostate cancer", "Prostatic Neoplasms", "D011471", TNM),
    ("renal", "Renal cell carcinoma", "Carcinoma, Renal Cell", "D002292", TNM),
    ("urothelial", "Bladder and urothelial cancer", "Urinary Bladder Neoplasms", "D001749", TNM),
    ("ovarian", "Ovarian cancer", "Ovarian Neoplasms", "D010051", FIGO),
    ("endometrial", "Endometrial cancer", "Endometrial Neoplasms", "D016889", FIGO),
    ("cervical", "Cervical cancer", "Uterine Cervical Neoplasms", "D002583", FIGO),
    ("melanoma", "Melanoma", "Melanoma", "D008545", TNM),
    ("head_and_neck", "Head and neck cancer", "Head and Neck Neoplasms", "D006258", TNM),
    ("glioma", "Glioma", "Glioma", "D005910", ["WHO grade"]),
    ("lymphoma", "Lymphoma", "Lymphoma", "D008223", ["Lugano (Ann Arbor)"]),
    ("myeloma", "Multiple myeloma", "Multiple Myeloma", "D009101", ["R-ISS"]),
    ("leukaemia", "Leukaemia", "Leukemia", "D007938", []),
    ("sarcoma", "Sarcoma", "Sarcoma", "D012509", TNM),
    ("unknown_primary", "Cancer of unknown primary", "Neoplasms, Unknown Primary", "D009382", []),
]


def upgrade() -> None:
    op.add_column("cancer_type", sa.Column("mesh_term", sa.Text(), nullable=True))
    op.add_column("cancer_type", sa.Column("mesh_id", sa.Text(), nullable=True))
    cancer_type = sa.table(
        "cancer_type",
        sa.column("key", sa.Text()), sa.column("display_name", sa.Text()), sa.column("mesh_term", sa.Text()),
        sa.column("mesh_id", sa.Text()), sa.column("staging_systems", postgresql.JSONB()),
    )
    op.bulk_insert(cancer_type, [
        {"key": key, "display_name": name, "mesh_term": term, "mesh_id": mesh_id, "staging_systems": systems}
        for key, name, term, mesh_id, systems in SHORTLIST
    ])


def downgrade() -> None:
    op.execute("DELETE FROM cancer_type WHERE key IN (" + ", ".join(f"'{row[0]}'" for row in SHORTLIST) + ")")
    op.drop_column("cancer_type", "mesh_id")
    op.drop_column("cancer_type", "mesh_term")
