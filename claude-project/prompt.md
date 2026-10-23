# Run prompt (vigil-run-prompt@1)

Start a new chat in the Vigil Project for each run. Attach the Patient's documents and their trial export, then paste everything below the line.

---

Run Vigil for this Patient (prompt version `vigil-run-prompt@1`). Today's date for this run is **{YYYY-MM-DD}**.

Attached:
- Documents: {list the file names}
- Trial export: {trials-….json}

Do this in order, following `vigil-method.md`:

1. **Extract** the Clinical Record from every document. Quote verbatim for every fact. List what trials will need that the documents don't give under `gaps`.
2. **Pick the target Cancer Diagnosis** and match against **every** trial in the export: parse each trial's criteria (attribute + scope), pre-filter on structured facts, adjudicate the rest, then set each trial's Match State.
3. **Write the run JSON** to a file named `run-{family_name}-{YYYY-MM-DD}.json`. It must validate against `vigil-run.schema.json`: check every required field and enum before you finish, and fix anything that doesn't fit rather than inventing a field.
4. **Render the Trial Briefing** from that JSON as a PDF named `briefing-{family_name}-{YYYY-MM-DD}.pdf`, laid out as in `vigil-method.md` §5.

Then reply with:
- both files, as downloads;
- a 5-line summary: target diagnosis; counts by Match State; the top gating gaps;
- anything you were unsure about (ambiguous or conflicting statements in the documents), with the document and quote.
