#!/bin/sh
# Rebuilds the synthetic documents: HTML from the p*_docs.py sources, then PDFs in the Playwright container (no host installs).
set -e
cd "$(dirname "$0")"
python3 _make.py
docker run --rm -v "$PWD":/work -w /work mcr.microsoft.com/playwright/python:v1.49.0-jammy \
  sh -c "pip install -q playwright==1.49.0 && python render.py"
