"""Read a resume from PDF / DOCX / TXT and keep its text for the whole session.

The extracted text is injected (condensed) into prompts so the tutor and the
mock-interviewer know the student's background, skills, and level.
"""

import os


def read_resume(path):
    """Return the plain text of a resume file. Raises ValueError on bad type."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)
    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    raise ValueError(
        f"Unsupported resume type '{ext}'. Please use a PDF, DOCX, or TXT file."
    )


def _read_pdf(path):
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PDF support needs PyMuPDF. Run: pip install PyMuPDF"
        ) from exc
    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def _read_docx(path):
    try:
        import docx  # python-docx
    except ImportError as exc:
        raise RuntimeError(
            "DOCX support needs python-docx. Run: pip install python-docx"
        ) from exc
    document = docx.Document(path)
    return "\n".join(p.text for p in document.paragraphs).strip()


def condense(text, limit=6000):
    """Collapse whitespace and cap length so prompts stay small and cheap."""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit] + " ...(truncated)"
