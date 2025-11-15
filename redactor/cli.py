import sys
from pathlib import Path

import click

from .redact import process_directory


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("sample"),
    show_default=True,
    help="Directory containing input PDFs.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("redacted"),
    show_default=True,
    help="Directory where redacted PDFs will be written.",
)
@click.option(
    "--log-csv",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("redaction_log.csv"),
    show_default=True,
    help="CSV path to write redaction log.",
)
def main(input_dir: Path, output_dir: Path, log_csv: Path) -> None:
    """Redact PII from text-based PDFs in a directory.

    Limitation: MVP does not perform OCR; scanned PDFs will be skipped.
    """
    try:
        process_directory(input_dir, output_dir, log_csv)
    except Exception as exc:  # pragma: no cover
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
