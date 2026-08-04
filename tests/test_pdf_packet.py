from pathlib import Path

from pypdf import PdfReader, PdfWriter

from marcus_cad.pdf_packet import merge_pdfs


def _one_page(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def test_merge_pdfs_preserves_order_and_page_count(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    _one_page(first)
    _one_page(second)
    output = merge_pdfs([first, second], tmp_path / "packet.pdf")
    assert output.exists()
    assert len(PdfReader(str(output)).pages) == 2
