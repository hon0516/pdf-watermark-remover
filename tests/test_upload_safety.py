import unittest
from email.message import Message
from types import SimpleNamespace

from watermark_remover.web.server import Handler, _safe_filename


class UploadSafetyTests(unittest.TestCase):
    def test_removes_unix_path_components(self):
        self.assertEqual(_safe_filename("../../private/input.pdf"), "input.pdf")

    def test_removes_windows_path_components(self):
        self.assertEqual(_safe_filename(r"C:\\private\\input.pdf"), "input.pdf")

    def test_adds_pdf_extension(self):
        self.assertEqual(_safe_filename("resume"), "resume.pdf")

    def test_uses_fallback_for_empty_name(self):
        self.assertEqual(_safe_filename("../"), "document.pdf")

    def test_allows_same_origin_local_requests(self):
        headers = Message()
        headers["Host"] = "127.0.0.1:8765"
        headers["Origin"] = "http://127.0.0.1:8765"

        self.assertTrue(Handler._is_local_origin(SimpleNamespace(headers=headers)))

    def test_rejects_remote_origin_even_with_matching_host_header(self):
        headers = Message()
        headers["Host"] = "attacker.example:8765"
        headers["Origin"] = "http://attacker.example:8765"

        self.assertFalse(Handler._is_local_origin(SimpleNamespace(headers=headers)))


if __name__ == "__main__":
    unittest.main()
