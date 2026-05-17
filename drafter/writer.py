"""
Document writer — saves cover letter + talking points as a single PDF.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from assets.candidate import load_candidate
from drafter.agent import DraftResult


def _sanitize(text: str) -> str:
    """Replace Unicode chars unsupported by Helvetica with ASCII equivalents."""
    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2022": "-", "\u2026": "...",
        "\u00a0": " ",
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00eb": "e",
        "\u00e0": "a", "\u00e2": "a", "\u00f4": "o",
        "\u00ee": "i", "\u00ef": "i",
        "\u00fb": "u", "\u00fc": "u",
        "\u00e7": "c", "\u00e6": "ae",
        "\u20ac": "EUR",  # € euro sign
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _strip_trailing_signature(text: str, candidate: dict) -> str:
    """Remove any closing sign-off Claude may have appended to the letter body."""
    sign_off_patterns = [
        "sincerely,", "yours sincerely,", "best regards,", "kind regards,",
        "regards,", "cordially,", "cordialement,", "bien cordialement,",
        "veuillez agréer", "dans l'attente",
    ]
    # Build name variants from candidate profile
    name = candidate.get("name", "").lower()
    name_ascii = candidate.get("name_ascii", "").lower()
    name_variants = {n for n in [name, name_ascii] if n}

    lines = text.rstrip().splitlines()
    while lines:
        stripped = lines[-1].strip().lower().rstrip(",").rstrip(".")
        is_sign_off = any(stripped.startswith(p.rstrip(",")) for p in sign_off_patterns)
        is_name = stripped in name_variants
        if is_sign_off or is_name or stripped == "":
            lines.pop()
        else:
            break
    return "\n".join(lines).strip()


def save_cover_letter(result: DraftResult, output_dir: str = "output") -> str:
    """Save cover letter + talking points as a single PDF. Returns file path."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    date_prefix = datetime.now().strftime("%Y%m")
    safe_company = re.sub(r"[^\w\s-]", "", result.company).strip().replace(" ", "_")[:30]
    safe_title = re.sub(r"[^\w\s-]", "", result.job_title).strip().replace(" ", "_")[:30]
    filename = f"{date_prefix}_CoverLetter_{safe_company}_{safe_title}.pdf"
    filepath = Path(output_dir) / filename

    pdf = FPDF(format="A4")
    pdf.set_margins(left=25, top=25, right=25)
    pdf.set_auto_page_break(auto=True, margin=20)

    # =========================================================
    # PAGE 1 — Cover Letter
    # =========================================================
    pdf.add_page()
    w = pdf.w - pdf.l_margin - pdf.r_margin  # usable width ~160mm

    c = load_candidate()

    # Candidate name
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 60, 100)
    pdf.cell(w, 8, _sanitize(c.get("name_ascii") or c["name"]), ln=True, align="R")

    # Contact line
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    contact = f"{c['email']}  |  {c['phone']}  |  {c['linkedin']}"
    pdf.cell(w, 5, _sanitize(contact), ln=True, align="R")
    pdf.cell(w, 5, _sanitize(c["location"]), ln=True, align="R")
    pdf.ln(8)

    # Date
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(w, 6, datetime.now().strftime("%B %d, %Y"), ln=True)
    pdf.ln(2)

    # Company + role
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(w, 6, _sanitize(result.company), ln=True)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(w, 6, _sanitize(f"Re: {result.job_title}"), ln=True)
    pdf.ln(8)

    # Body paragraphs
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    clean_letter = _strip_trailing_signature(result.cover_letter, c)
    for para in clean_letter.split("\n\n"):
        para = para.strip().replace("\n", " ")
        if not para:
            continue
        pdf.multi_cell(w, 6, _sanitize(para), align="J")
        pdf.ln(4)

    pdf.ln(6)

    # Signature
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(w, 6, "Sincerely,")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(w, 6, _sanitize(c.get("name_ascii") or c["name"]), ln=True)

    # =========================================================
    # PAGE 2 — Talking Points
    # =========================================================
    if result.talking_points:
        pdf.add_page()
        # Recalculate w after add_page resets cursor
        w = pdf.w - pdf.l_margin - pdf.r_margin

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 60, 100)
        pdf.set_x(pdf.l_margin)
        pdf.cell(w, 8, "Resume Talking Points", ln=True)

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.set_x(pdf.l_margin)
        pdf.cell(w, 5, _sanitize(f"{result.job_title} @ {result.company}"), ln=True)
        pdf.ln(3)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)

        for line in result.talking_points.split("\n"):
            line = line.strip()
            if not line:
                pdf.ln(2)
                continue
            pdf.set_x(pdf.l_margin)
            if line.startswith("**") and line.endswith("**"):
                pdf.set_font("Helvetica", "B", 10)
                pdf.multi_cell(w, 5, _sanitize(line.strip("*").strip()))
                pdf.set_font("Helvetica", "", 10)
            elif line.startswith("- ") or line.startswith("* "):
                pdf.multi_cell(w, 5, _sanitize("- " + line[2:]))
            else:
                pdf.multi_cell(w, 5, _sanitize(line))

    pdf.output(str(filepath))
    return str(filepath)
