"""Therapeutic groups: the top level of the WHO ATC classification, which the PBS Schedule API gives each PBS
Item. ATC files a drug by its main use (duloxetine is an antidepressant even when prescribed for pain), so a
group is a way to browse, not a statement of what a drug may be used for.
"""

GROUPS = {
    "A": "Alimentary tract and metabolism",
    "B": "Blood and blood forming organs",
    "C": "Cardiovascular system",
    "D": "Dermatologicals",
    "G": "Genito-urinary system and sex hormones",
    "H": "Systemic hormonal preparations",
    "J": "Anti-infectives for systemic use",
    "L": "Antineoplastic and immunomodulating agents",
    "M": "Musculo-skeletal system",
    "N": "Nervous system",
    "P": "Antiparasitic products",
    "R": "Respiratory system",
    "S": "Sensory organs",
    "V": "Various",
}
# The "Cancer drugs" shortcut: antineoplastic agents (L01) and endocrine therapy (L02).
CANCER = "cancer"
CANCER_LABEL = "Cancer drugs (ATC L01, L02)"
CANCER_PREFIXES = ("L01", "L02")


def label(group: str) -> str:
    return GROUPS.get(group, group)
