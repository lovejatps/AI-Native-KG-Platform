"""Document loader with multi‑backend support.

The loader attempts the following strategies in order:
1. **unstructured** – preferred high‑level parser.
2. **Apache Tika** – via ``tika`` Python wrapper.
3. **pdfminer.six** – low‑level PDF text extraction.
4. **OCR** – renders each PDF page to an image (using ``pdf2image``) and runs
   ``pytesseract``.  This is the most heavyweight fallback and only runs when all
   previous methods fail.

If none of the libraries are available the function returns a clear placeholder
string indicating that no parser could be loaded.
"""

# ---------------------------------------------------------------------------
# 1. Attempt to import the preferred ``unstructured`` parser.
# ---------------------------------------------------------------------------
try:
    from unstructured.partition.pdf import partition_pdf  # type: ignore
except Exception:  # pragma: no cover – fallback defined below
    partition_pdf = None

# ---------------------------------------------------------------------------
# 2. Optional Tika import.
# ---------------------------------------------------------------------------
try:
    from tika import parser as tika_parser  # type: ignore
except Exception:
    tika_parser = None

# ---------------------------------------------------------------------------
# 3. Optional pdfminer import.
# ---------------------------------------------------------------------------
try:
    from pdfminer.high_level import extract_text  # type: ignore
except Exception:
    extract_text = None

# ---------------------------------------------------------------------------
# 4. Optional OCR imports.
# ---------------------------------------------------------------------------
try:
    from pdf2image import convert_from_path  # type: ignore
    import pytesseract  # type: ignore
except Exception:
    convert_from_path = None
    pytesseract = None

import os
from typing import List


def _ocr_fallback(file_path: str) -> str:
    """Render PDF pages to images and run OCR.
    Returns concatenated OCR text or a placeholder if OCR libraries are missing.
    """
    if not (convert_from_path and pytesseract):
        return "[OCR unavailable – missing pdf2image/pytesseract]"
    try:
        images = convert_from_path(file_path)
        texts: List[str] = []
        for img in images:
            texts.append(pytesseract.image_to_string(img))
        return "\n".join(texts)
    except Exception:
        return "[OCR failed]"


def load_pdf(file_path: str) -> str:
    """Load a document (PDF or Markdown) using the best available backend.
    Returns the extracted plain‑text representation.
    """
    # ==== Markdown fallback ====
    if file_path.lower().endswith((".md", ".markdown")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "[Failed to read markdown file]"

    # 1️⃣ Try unstructured (high‑level, retains layout info)
    if partition_pdf:
        try:
            elements = partition_pdf(file_path)
            return "\n".join([str(e) for e in elements])
        except Exception:
            pass

    # 2️⃣ Try Apache Tika (uses Java under the hood)
    if tika_parser:
        try:
            parsed = tika_parser.from_file(file_path)
            return parsed.get("content", "") or "[Tika returned empty content]"
        except Exception:
            pass

    # 3️⃣ Try pdfminer (pure Python, reliable for text PDFs)
    if extract_text:
        try:
            return extract_text(file_path) or "[pdfminer returned empty content]"
        except Exception:
            pass

    # 4️⃣ OCR fallback – image based extraction
    return _ocr_fallback(file_path)
