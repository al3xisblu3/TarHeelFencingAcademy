import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import fitz  # PyMuPDF


@dataclass
class MatchInfo:
    label: str
    pattern: str
    text: str
    page_index: int
    rects: List[fitz.Rect]


DEFAULT_PATTERNS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    # Simple US phone (very permissive)
    "phone": r"(?:(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4})",
    # US SSN
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    # Credit card (basic, may over-match). Luhn not applied here for MVP.
    "cc": r"\b(?:\d[ -]*?){13,16}\b",
}


def _is_scanned_pdf(doc: fitz.Document, min_text_chars: int = 10) -> bool:
    """Heuristic: if all pages have very little selectable text, treat as scanned.
    MVP limitation: we do not perform OCR; scanned PDFs will be skipped.
    """
    for page in doc:  # type: ignore[assignment]
        text = page.get_text("text") or ""
        if len(text.strip()) >= min_text_chars:
            return False
    return True


def _iter_literal_rects(page: fitz.Page, literal: str) -> List[fitz.Rect]:
    """Find all rectangles for a literal string using page.search_for.
    For regex matches, we pass the exact matched substring as literal.
    """
    rects: List[fitz.Rect] = []
    # search_for can find multiple occurrences; flags=0 for default, quads returned as rects
    for r in page.search_for(literal):
        rects.append(r)
    return rects


def _find_matches(page: fitz.Page, patterns: dict) -> List[MatchInfo]:
    text = page.get_text("text") or ""
    matches: List[MatchInfo] = []
    for label, pat in patterns.items():
        for m in re.finditer(pat, text):
            literal = m.group(0)
            rects = _iter_literal_rects(page, literal)
            if rects:
                matches.append(
                    MatchInfo(
                        label=label, pattern=pat, text=literal, page_index=page.number, rects=rects
                    )
                )
    return matches


def redact_pdf(input_path: Path | str, output_path: Path | str, patterns: dict | None = None) -> List[Tuple[int, str, str, fitz.Rect]]:
    """Redact a single PDF and save to output_path.

    Returns a list of tuples describing redactions: (page_index, label, text, rect)
    """
    patterns = patterns or DEFAULT_PATTERNS
    input_path = Path(input_path)
    output_path = Path(output_path)

    redactions: List[Tuple[int, str, str, fitz.Rect]] = []

    with fitz.open(input_path) as doc:
        if _is_scanned_pdf(doc):
            # Skip scanned PDFs (no OCR in MVP)
            return redactions

        for page in doc:  # type: ignore[assignment]
            matches = _find_matches(page, patterns)
            for mi in matches:
                for rect in mi.rects:
                    # Add a redaction annotation covering the rect
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    redactions.append((mi.page_index, mi.label, mi.text, rect))
            # Apply per-page to avoid stale annots; safe to call multiple times
            page.apply_redactions()

        # Save redacted document
        doc.save(output_path)

    return redactions


def process_directory(
    input_dir: Path | str,
    output_dir: Path | str,
    log_csv: Path | str,
    patterns: dict | None = None,
) -> None:
    """Process all PDFs in a directory, write redacted PDFs and a CSV log."""
    patterns = patterns or DEFAULT_PATTERNS
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    log_csv = Path(log_csv)

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(log_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "page", "label", "matched_text", "left", "top", "right", "bottom"])

        for pdf_path in sorted(input_dir.glob("*.pdf")):
            out_path = output_dir / pdf_path.name
            with fitz.open(pdf_path) as doc:
                if _is_scanned_pdf(doc):
                    # Skip scanned PDFs and note in log with page = -1
                    writer.writerow([pdf_path.name, -1, "skipped_scanned_pdf", "", "", "", "", ""])
                    continue

            redactions = redact_pdf(pdf_path, out_path, patterns=patterns)
            for page_index, label, text, rect in redactions:
                writer.writerow(
                    [
                        pdf_path.name,
                        page_index + 1,  # 1-based page index in log
                        label,
                        text,
                        f"{rect.x0:.2f}",
                        f"{rect.y0:.2f}",
                        f"{rect.x1:.2f}",
                        f"{rect.y1:.2f}",
                    ]
                )
