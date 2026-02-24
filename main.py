"""FastAPI application – Validador de Documentos Académicos."""

import shutil
import uuid
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from utils.analyzer import analyze_document
from utils.file_processor import extract_text
from utils.report_generator import generate_word_report

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Validador de Documentos Académicos")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("uploads")
REPORTS_DIR = Path("reports")
UPLOAD_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
async def analyze(
    reference_files: List[UploadFile] = File(..., description="Archivos de referencia (PDF/DOCX/TXT)"),
    eval_file: UploadFile = File(..., description="Documento a evaluar (PDF/DOCX/TXT)"),
) -> JSONResponse:
    if not reference_files:
        raise HTTPException(400, "Debes subir al menos un documento de referencia.")

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Save & extract reference files ────────────────────────────────────
        reference_texts: list[dict] = []
        for ref in reference_files:
            _validate_extension(ref.filename)
            saved = await _save_upload(ref, session_dir)
            text = extract_text(saved)
            reference_texts.append({"name": ref.filename, "content": text})

        # ── Save & extract evaluation file ────────────────────────────────────
        _validate_extension(eval_file.filename)
        eval_saved = await _save_upload(eval_file, session_dir)
        eval_text = extract_text(eval_saved)

        # ── Run analysis ──────────────────────────────────────────────────────
        analysis = await analyze_document(reference_texts, eval_text, eval_file.filename)

        # ── Generate Word report ──────────────────────────────────────────────
        report_name = f"reporte_{session_id[:8]}.docx"
        report_path = REPORTS_DIR / report_name
        generate_word_report(analysis, eval_file.filename, report_path)

        return JSONResponse(
            {
                "success": True,
                "analysis": analysis,
                "report_filename": report_name,
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Error durante el análisis: {exc}") from exc

    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


@app.get("/download/{filename}")
async def download_report(filename: str) -> FileResponse:
    # Sanitise to prevent path traversal
    safe_name = Path(filename).name
    report_path = REPORTS_DIR / safe_name

    if not report_path.exists() or report_path.suffix != ".docx":
        raise HTTPException(404, "Reporte no encontrado.")

    return FileResponse(
        report_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        filename=safe_name,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _validate_extension(filename: Optional[str]) -> None:
    if not filename:
        raise HTTPException(400, "Nombre de archivo vacío.")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Formato '{ext}' no soportado. Use PDF, DOCX o TXT.",
        )


async def _save_upload(upload: UploadFile, directory: Path) -> Path:
    dest = directory / (upload.filename or "archivo")
    async with aiofiles.open(dest, "wb") as f:
        content = await upload.read()
        await f.write(content)
    return dest


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
