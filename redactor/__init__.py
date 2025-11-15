"""PDF Redaction MVP (no OCR).

Exposes:
- redact_pdf: redact a single PDF
- process_directory: CLI helper to process a directory of PDFs
"""
from .redact import redact_pdf, process_directory
