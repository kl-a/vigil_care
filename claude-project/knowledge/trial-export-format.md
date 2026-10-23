# The trial export file

Vigil's ClinicalTrials.gov Refresh stores a trial snapshot; for each Patient it exports the candidate trials as one JSON file, `trials-<pseudonym>-<date>.json`. That file is the **only** source of trials for a run.

```json
{
  "export_id": "tx-2026-10-23-VG-0051",
  "snapshot_id": "uuid of the trial snapshot",
  "taken_at": "2026-10-23T02:00:00Z",
  "registry": "CTGOV",
  "query": {"condition": "non-small cell lung cancer", "country": "Australia", "statuses": ["RECRUITING", "NOT_YET_RECRUITING"]},
  "distance_from": "Hurstville NSW 2220 (Patient's suburb)",
  "trials": [
    {
      "nct_id": "NCT00000000",
      "title": "…",
      "sponsor": "…",
      "phase": "PHASE1",
      "overall_status": "RECRUITING",
      "conditions": ["…"],
      "interventions": [{"type": "DRUG", "name": "…", "description": "…"}],
      "brief_summary": "…",
      "eligibility_text": "Inclusion Criteria:\n…\nExclusion Criteria:\n…",
      "minimum_age": "18 Years",
      "maximum_age": null,
      "sex": "ALL",
      "last_updated": "2026-10-01",
      "sites": [
        {"facility": "…", "city": "…", "state": "New South Wales", "site_status": "RECRUITING", "distance_km": 14.2}
      ]
    }
  ]
}
```

- `sites` holds Australian sites only, nearest first. `distance_km` is straight-line from `distance_from` (approximate; null when a site has no location).
- `eligibility_text` is verbatim from the registry. Quote criteria from it exactly.
