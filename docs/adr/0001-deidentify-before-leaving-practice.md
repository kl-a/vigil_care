# De-identify before anything leaves the Practice Boundary; OCR locally first

Documents are read inside the Practice Boundary: the practice's own machines on its own network, such as the main workstation, a GPU worker or a local server. We use local OCR and local VLMs, and these may see identifiable pages. Before anything goes outside that boundary, including a cloud vision model (Claude or another VLM) as a last resort, the page is de-identified. Only the masked image or pseudonymised text is sent, tagged with a one-off request ID; the ledger that maps each request ID back to its Document stays inside. This reverses the v1.1 design, which sent raw degraded images to Claude vision first.

## Considered Options

- **Boundary = a single device.** Rejected. It would stop us using a separate GPU worker (the RTX 2060 box) or a small local server to read unmasked pages. Those machines are practice-owned, so they fall inside the boundary.

## Consequences

- Identifiable data moving between practice machines must be encrypted in transit. Worker machines should not store documents after processing them.
- Masking needs to know where the PII sits on the page, so local OCR that returns word positions runs before any cloud fallback.
- If local OCR can't find all the PII with enough confidence (e.g. on a bad fax), the page goes to manual redaction. It is never sent out.
- Masked output must also be stripped of the PDF text layer, EXIF metadata, filename and any barcodes or QR codes, or PII still leaves the practice.
- The local OCR stack is provisional. See [revisit-later.md](../revisit-later.md) #1.
