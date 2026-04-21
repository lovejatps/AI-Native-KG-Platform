"""Placeholder loader for .docx files.

In a full implementation this would use ``python-docx`` to extract paragraphs
and tables. For Phase‑2 we expose a simple function that returns the raw text
content of the file.
"""

import os


def load_docx(file_path: str) -> str:
    """Read a .docx file and return its text content.

    This stub reads the file as binary and returns a placeholder string –
    replace with ``docx.Document`` parsing for production.
    """
    if not file_path.lower().endswith(".docx"):
        raise ValueError("File must have .docx extension")
    # Simple placeholder – real implementation would parse the document
    return f"[DOCX content of {os.path.basename(file_path)}]"
