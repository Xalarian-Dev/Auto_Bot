"""
Resume reader — extracts text from the candidate's PDF resume.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_resume_text(pdf_path: str) -> str:
    """Extract all text from the PDF resume."""
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def get_resume_text(assets_dir: str = "assets") -> str:
    """Find and read the first PDF in the assets directory."""
    assets = Path(assets_dir)
    pdfs = list(assets.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF found in {assets_dir}")
    return extract_resume_text(str(pdfs[0]))
