from pathlib import Path

import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: Path) -> str:
    doc = fitz.open(str(file_path))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)
