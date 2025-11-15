from __future__ import annotations

import csv
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from redactor.redact import process_directory, redact_pdf


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    return input_dir, output_dir


def _make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    # Place text at a visible location
    page.insert_text((72, 100), text, fontsize=12)
    doc.save(path)
    doc.close()


def test_redact_pdf_single_file(tmp_path: Path):
    src = tmp_path / "src.pdf"
    dst = tmp_path / "dst.pdf"
    email = "contact.me+test@example.com"
    _make_pdf(src, f"Please email {email} for info.")

    redactions = redact_pdf(src, dst)

    assert dst.exists(), "Redacted PDF should be created"
    assert redactions, "Expected at least one redaction"

    # Ensure original literal is no longer selectable text
    with fitz.open(dst) as out_doc:
        text = "".join(page.get_text("text") for page in out_doc)
        assert email not in text


def test_process_directory_logs_and_outputs(tmp_dirs: tuple[Path, Path], tmp_path: Path):
    input_dir, output_dir = tmp_dirs
    log_csv = tmp_path / "redaction_log.csv"

    # Create multiple PDFs
    _make_pdf(input_dir / "a.pdf", "Call me at 919-555-1234")
    _make_pdf(input_dir / "b.pdf", "Email: user@example.com")

    process_directory(input_dir, output_dir, log_csv)

    # Outputs should exist
    assert (output_dir / "a.pdf").exists()
    assert (output_dir / "b.pdf").exists()

    # Log should have header + at least one data row
    assert log_csv.exists()
    with open(log_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows and rows[0] == [
        "file",
        "page",
        "label",
        "matched_text",
        "left",
        "top",
        "right",
        "bottom",
    ]
    assert len(rows) >= 2
