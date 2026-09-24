# No AGPL PDF libraries: pypdfium2 + pikepdf instead of PyMuPDF

The v1.1 design used PyMuPDF for native-PDF text extraction, and PyMuPDF is the most capable Python redaction library. We don't use it. It is AGPL-3.0, and shipping Vigil (even as a Docker image to one practice) would bring the whole application under the AGPL unless we bought an Artifex commercial licence. We use pypdfium2 (Apache-2.0/BSD-3) for text extraction and rendering pages to images, and pikepdf (MPL-2.0) for stripping metadata.

## Consequences

- Redaction burn-in works by rendering each page to an image, blacking out the boxes, and rebuilding the PDF from those images only. Redacted exports lose text quality, but no original content can survive.
- If someone later suggests "just use PyMuPDF", the answer is the licence. Buying the commercial licence is the only way to reopen this.
