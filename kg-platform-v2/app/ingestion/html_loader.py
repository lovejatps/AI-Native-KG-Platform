"""Placeholder loader for .html files.

Extracts text from HTML using ``BeautifulSoup`` in a production version. This
stub simply reads the file content.
"""

import os


def load_html(file_path: str) -> str:
    if not file_path.lower().endswith(".html"):
        raise ValueError("File must have .html extension")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
