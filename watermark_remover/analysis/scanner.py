from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


# Recognize a clipped, tiled Pattern paint block at the end of a page stream.
_PATTERN_TAIL = re.compile(
    rb"q\s+0 0 [0-9.]+ [0-9.]+ re\s+W\*\s+n\s+q\s+"
    rb"(?:[-+]?[0-9]*\.?[0-9]+\s+){6}cm\s+"
    rb"/Pattern CS/Pattern cs/P\w+ SCN/P\w+ scn\s+/G\d+ gs\s+"
    rb"0 0 [0-9.]+ [0-9.]+ re\s+f\s+Q\s+Q\s*$",
    re.S,
)


def analyze_pdf(path: str | Path, max_pages: int = 100) -> dict:
    reader = PdfReader(str(path), strict=False)
    if reader.is_encrypted:
        raise ValueError("暂不支持加密 PDF")
    if len(reader.pages) > max_pages:
        raise ValueError(f"PDF 页数超过限制（最多 {max_pages} 页）")

    candidates = []
    for page_number, page in enumerate(reader.pages, 1):
        contents = page.get("/Contents")
        if contents is None:
            data = b""
        elif isinstance(contents, (list, tuple)):
            data = b"\n".join(item.get_object().get_data() for item in contents)
        else:
            data = contents.get_object().get_data()
        match = _PATTERN_TAIL.search(data)
        if not match:
            continue
        candidates.append(
            {
                "id": f"p{page_number}-pattern",
                "page": page_number,
                "type": "pattern",
                "label": "平铺图案水印",
                "confidence": 0.96,
                "default_selected": True,
                "safe": True,
                "description": "页面末尾可定位的裁剪式 Pattern 平铺图层",
            }
        )

    return {
        "pages": len(reader.pages),
        "candidates": candidates,
        "metadata": {"title": reader.metadata.title if reader.metadata else None},
    }


def remove_pattern_tail(data: bytes) -> tuple[bytes, bool]:
    match = _PATTERN_TAIL.search(data)
    if not match:
        return data, False
    return data[: match.start()] + b"\n", True
