from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import cairosvg
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


def create_blocked_calls_report(
    blocked_calls: Sequence[tuple[int, str, list[dict[str, str]]]],
    output_path: Path,
) -> Path:
    """Create a printable PDF page listing calls that could not render."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for index, call, blockers in blocked_calls:
        lines.append(f"{index}. {call}")
        if blockers:
            for blocker in blockers:
                obj = str(blocker.get("object", "UNKNOWN"))
                reason = str(blocker.get("reason", "BLOCKED"))
                lines.append(f"   - {obj}: {reason}")
                suggestion = blocker.get("suggested_calls")
                if suggestion:
                    lines.append(f"     Use: {suggestion}")
        else:
            lines.append("   - Card could not be generated.")

    def escape(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    y = 125
    text_nodes: list[str] = []
    for line in lines:
        if y > 730:
            break
        text_nodes.append(
            f'<text x="54" y="{y}" font-family="Arial, sans-serif" font-size="13">{escape(line)}</text>'
        )
        y += 21

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="612" height="792" viewBox="0 0 612 792">'
        '<rect width="612" height="792" fill="white"/>'
        '<text x="54" y="60" font-family="Arial, sans-serif" font-size="24" font-weight="700">Marcus Offensive CAD</text>'
        '<text x="54" y="91" font-family="Arial, sans-serif" font-size="18" font-weight="700">Blocked Calls Report</text>'
        + "".join(text_nodes)
        + "</svg>"
    )
    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(output_path))
    return output_path
