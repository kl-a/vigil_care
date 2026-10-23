"""Renders every patients/*/src/*.html to patients/*/documents/*.pdf (text PDFs). Run inside the Playwright image; see render.sh."""
import glob, os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for src in sorted(glob.glob("/work/*/src/*.html")):
        out_dir = os.path.join(os.path.dirname(os.path.dirname(src)), "documents")
        os.makedirs(out_dir, exist_ok=True)
        page.goto("file://" + src)
        page.pdf(path=os.path.join(out_dir, os.path.basename(src)[:-5] + ".pdf"), format="A4", print_background=True, prefer_css_page_size=True)
        print("rendered", src)
    browser.close()
