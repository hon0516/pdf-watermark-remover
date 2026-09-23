# Contributing

Thanks for helping improve the project.

## Before opening an issue

- Check existing issues for duplicates.
- For PDF compatibility reports, use a minimal document with no personal or confidential information.
- Describe the PDF producer, the expected result, and what actually happened.

## Development checks

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Please add or update tests for behavior changes. Keep processing local, do not add telemetry, and do not commit PDFs containing personal information.

## Pull requests

Keep changes focused, explain user-visible behavior, and include the tests you ran. New watermark-removal patterns should be conservative and must not remove page content outside the selected watermark block.
