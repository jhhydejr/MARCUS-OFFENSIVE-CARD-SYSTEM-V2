from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter


class PdfPacketError(Exception):
    pass


def merge_pdfs(pdf_paths: Iterable[Path], output_path: Path) -> Path:
    """Merge PDFs in the supplied order into one printable packet."""
    paths = [Path(path) for path in pdf_paths]
    if not paths:
        raise PdfPacketError("No rendered card PDFs were available for the packet.")

    writer = PdfWriter()
    for path in paths:
        if not path.is_file():
            raise PdfPacketError(f"Missing card PDF: {path}")
        reader = PdfReader(str(path))
        if not reader.pages:
            raise PdfPacketError(f"Card PDF contains no pages: {path}")
        for page in reader.pages:
            writer.add_page(page)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path
