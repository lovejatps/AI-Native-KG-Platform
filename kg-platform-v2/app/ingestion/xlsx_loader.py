"""Placeholder loader for .xlsx/.xlsm files.

Uses ``openpyxl`` in a real implementation; here we provide a stub that returns
CSV‑like string for simplicity.
"""

import os


def load_xlsx(file_path: str) -> str:
    if not file_path.lower().endswith((".xlsx", ".xlsm")):
        raise ValueError("File must be an Excel workbook")
    # Stub – real implementation would read sheets and convert to text
    return f"[XLSX content of {os.path.basename(file_path)}]"
