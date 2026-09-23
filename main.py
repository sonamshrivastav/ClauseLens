import os
import uuid
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from parser import DocumentParser
from ai_engine import ai_engine

logger = logging.getLogger("legal_ai")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="ClauseLens AI — Legal Document Intelligence Platform",
    description="Backend API powering ClauseLens legal document factual analysis, blind spots identification, and grounded Q&A.",
    version="3.0.0"
)

# In-memory document store
DOCUMENT_STORE: Dict[str, Dict[str, Any]] = {}

class TextAnalysisRequest(BaseModel):
    text: str
    doc_title: Optional[str] = "Pasted Contract Document"
    provider: Optional[str] = "auto"

class QARequest(BaseModel):
    doc_id: str
    question: str
    provider: Optional[str] = "auto"


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    provider: str = Form("auto")
):
    """Upload PDF or TXT contract file for factual clause analysis."""
    filename = file.filename
    content_type = file.content_type or ""
    contents = await file.read()

    try:
        from fastapi.concurrency import run_in_threadpool

        if filename.lower().endswith(".pdf") or "pdf" in content_type.lower():
            raw_text = await run_in_threadpool(DocumentParser.extract_text_from_pdf, contents)
        else:
            raw_text = DocumentParser.extract_text_from_txt(contents)

        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from uploaded file.")

        raw_clauses = DocumentParser.parse_document_to_clauses(raw_text)
        from fastapi.concurrency import run_in_threadpool
        analysis_result = await run_in_threadpool(ai_engine.analyze_clauses, raw_clauses, provider)

        doc_id = str(uuid.uuid4())[:8]
        DOCUMENT_STORE[doc_id] = {
            "id": doc_id,
            "title": filename,
            "rawText": raw_text,
            "clauses": raw_clauses,
            "analysis": analysis_result
        }

        return {
            "doc_id": doc_id,
            "title": filename,
            "analysis": analysis_result
        }
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-text")
async def analyze_text(req: TextAnalysisRequest):
    """Analyze raw pasted text."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text payload cannot be empty.")

    try:
        raw_clauses = DocumentParser.parse_document_to_clauses(req.text)
        from fastapi.concurrency import run_in_threadpool
        analysis_result = await run_in_threadpool(ai_engine.analyze_clauses, raw_clauses, req.provider)

        doc_id = str(uuid.uuid4())[:8]
        DOCUMENT_STORE[doc_id] = {
            "id": doc_id,
            "title": req.doc_title,
            "rawText": req.text,
            "clauses": raw_clauses,
            "analysis": analysis_result
        }

        return {
            "doc_id": doc_id,
            "title": req.doc_title,
            "analysis": analysis_result
        }
    except Exception as e:
        logger.error(f"Error processing pasted text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_with_doc(req: QARequest):
    """Grounded Q&A strictly against document context."""
    if req.doc_id not in DOCUMENT_STORE:
        raise HTTPException(status_code=404, detail="Document session not found. Please re-upload your file.")

    doc_data = DOCUMENT_STORE[req.doc_id]
    clauses = doc_data.get("clauses", [])

    from fastapi.concurrency import run_in_threadpool
    answer_data = await run_in_threadpool(ai_engine.answer_question, clauses, req.question, req.provider)
    return answer_data

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

from fastapi.responses import HTMLResponse, RedirectResponse

@app.get("/", response_class=RedirectResponse)
async def serve_index():
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
