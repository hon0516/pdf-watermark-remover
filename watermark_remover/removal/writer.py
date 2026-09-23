from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from ..analysis.scanner import remove_pattern_tail


def _page_content_data(page) -> bytes:
    contents = page.get("/Contents")
    if contents is None:
        return b""
    if isinstance(contents, (list, tuple)):
        return b"\n".join(item.get_object().get_data() for item in contents)
    return contents.get_object().get_data()


def remove_watermarks(source: str | Path, destination: str | Path, selected: list[str]):
    reader = PdfReader(str(source), strict=False)
    if reader.is_encrypted:
        raise ValueError("暂不支持加密 PDF")

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    selected_ids = set(selected)
    removed = []

    for page_number, page in enumerate(writer.pages, 1):
        data = _page_content_data(page)
        candidate_id = f"p{page_number}-pattern"
        if candidate_id in selected_ids:
            data, changed = remove_pattern_tail(data)
            if changed:
                removed.append(candidate_id)
        stream = DecodedStreamObject()
        stream.set_data(data)
        page[NameObject("/Contents")] = writer._add_object(stream)

    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        writer.write(stream)
    return removed, len(writer.pages)
