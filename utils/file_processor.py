"""Extract text content from PDF, DOCX, and TXT files."""

from pathlib import Path


MAX_CHARS = 120_000  # ~30K tokens; stays well within Claude's 200K context


def extract_text(file_path: Path) -> str:
    """Extract plain text from a file based on its extension."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        text = _extract_from_pdf(file_path)
    elif ext == ".docx":
        text = _extract_from_docx(file_path)
    elif ext == ".txt":
        text = _extract_from_txt(file_path)
    else:
        raise ValueError(f"Formato no soportado: {ext!r}. Use PDF, DOCX o TXT.")

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[... Texto truncado por longitud ...]"

    return text.strip()


def _extract_from_pdf(file_path: Path) -> str:
    import fitz  # PyMuPDF

    pages: list[str] = []
    with fitz.open(file_path) as doc:
        for page in doc:
            page_text = page.get_text()
            if page_text.strip():
                pages.append(page_text)
    return "\n\n".join(pages)


def _extract_from_docx(file_path: Path) -> str:
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_from_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="replace")
