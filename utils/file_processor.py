"""Extract text content from PDF, DOCX, TXT, and Excel files."""

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
    elif ext == ".xlsx":
        text = _extract_from_xlsx(file_path)
    elif ext == ".xls":
        text = _extract_from_xls(file_path)
    else:
        raise ValueError(f"Formato no soportado: {ext!r}. Use PDF, DOCX, TXT, XLSX o XLS.")

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


def _extract_from_xlsx(file_path: Path) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheets: list[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows: list[str] = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None and str(c).strip()]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            sheets.append(f"[Hoja: {sheet_name}]\n" + "\n".join(rows))
    wb.close()
    return "\n\n".join(sheets)


def _extract_from_xls(file_path: Path) -> str:
    import xlrd

    wb = xlrd.open_workbook(str(file_path))
    sheets: list[str] = []
    for sheet_name in wb.sheet_names():
        ws = wb.sheet_by_name(sheet_name)
        rows: list[str] = []
        for row_idx in range(ws.nrows):
            cells = [
                str(ws.cell_value(row_idx, col))
                for col in range(ws.ncols)
                if str(ws.cell_value(row_idx, col)).strip()
            ]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            sheets.append(f"[Hoja: {sheet_name}]\n" + "\n".join(rows))
    return "\n\n".join(sheets)
