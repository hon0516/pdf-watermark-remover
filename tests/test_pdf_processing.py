import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from watermark_remover.analysis import analyze_pdf
from watermark_remover.removal import remove_watermarks


PATTERN_WATERMARK = b"""q
0 0 2475.9165 3502.166 re
W* n
q
3.5882847 0 0 3.5882847 0 0 cm
/Pattern CS/Pattern cs/P100 SCN/P100 scn
/G3 gs
0 0 689 2832 re
f
Q
Q
"""


def create_pdf(path: Path, add_watermark: bool = True) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    content = b"% retained page content\n"
    if add_watermark:
        content += PATTERN_WATERMARK
    stream = DecodedStreamObject()
    stream.set_data(content)
    page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as output:
        writer.write(output)


def read_content(path: Path) -> bytes:
    page = PdfReader(str(path)).pages[0]
    contents = page.get("/Contents")
    return contents.get_object().get_data()


class PdfProcessingTests(unittest.TestCase):
    def test_recognizes_supported_tiled_pattern(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "pattern.pdf"
            create_pdf(source)

            result = analyze_pdf(source)

            self.assertEqual(result["pages"], 1)
            self.assertEqual([candidate["id"] for candidate in result["candidates"]], ["p1-pattern"])
            self.assertTrue(result["candidates"][0]["default_selected"])

    def test_removes_selected_pattern_and_preserves_other_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            output = Path(temp_dir) / "output.pdf"
            create_pdf(source)

            removed, pages = remove_watermarks(source, output, ["p1-pattern"])
            content = read_content(output)

            self.assertEqual(removed, ["p1-pattern"])
            self.assertEqual(pages, 1)
            self.assertIn(b"retained page content", content)
            self.assertNotIn(b"/Pattern CS", content)
            self.assertIn(b"/Pattern CS", read_content(source))

    def test_unselected_pattern_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            output = Path(temp_dir) / "output.pdf"
            create_pdf(source)

            removed, _ = remove_watermarks(source, output, [])

            self.assertEqual(removed, [])
            self.assertIn(b"/Pattern CS", read_content(output))

    def test_pdf_without_supported_pattern_has_no_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "plain.pdf"
            create_pdf(source, add_watermark=False)

            result = analyze_pdf(source)

            self.assertEqual(result["candidates"], [])

    def test_page_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "one-page.pdf"
            create_pdf(source)

            with self.assertRaisesRegex(ValueError, "页数超过限制"):
                analyze_pdf(source, max_pages=0)


if __name__ == "__main__":
    unittest.main()
