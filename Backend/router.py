from fastapi import APIRouter, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse
from celery.result import AsyncResult
from celery_config import celery_app
from tasks import convert_text_to_audio
from pathlib import Path
from uuid import uuid4
import shutil
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import pdfplumber
from io import BytesIO
import asyncio
import tasks  # Add this import

api_router = APIRouter()

# -----------------------------------------------------------------------------
# Paths & config
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "originals"
AUDIO_DIR = STATIC_DIR / "audio"

for d in (UPLOAD_DIR, AUDIO_DIR):
    d.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".epub"}
MAX_FILE_SIZE_MB = 30

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@api_router.post("/files")
async def upload_file(file: UploadFile):
    """Save the incoming PDF/EPUB and return its generated *file_id*."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported file type")

    # Naïve size guard (UploadFile doesn't expose size, but our reverse proxy might)
    if getattr(file, "size", None) and file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, "File too large")

    file_id = uuid4().hex
    dest_path = UPLOAD_DIR / f"{file_id}{suffix}"

    with dest_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    return {"file_id": file_id}

@api_router.post("/tasks")
async def start_conversion(file_id: str = Query(..., alias="file_id")):
    """Kick off the Celery TTS task for a stored file."""
    
    # Find the file
    original_path = next(UPLOAD_DIR.glob(f"{file_id}.*"), None)
    if not original_path:
        raise HTTPException(404, "File not found")
    
    # Read and validate file content
    try:
        # Check if it's a PDF or text file based on extension
        ext = original_path.suffix.lower()
        
        if ext == '.pdf':
            # Extract text from PDF
            content = original_path.read_bytes()
            text_content = ""
            try:
                with pdfplumber.open(BytesIO(content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {str(e)}")
            
            if not text_content.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")
                
        elif ext == '.epub':
            # Extract text from EPUB
            content = original_path.read_bytes()
            text_content = ""
            try:
                book = epub.read_epub(BytesIO(content))
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        text_content += soup.get_text() + "\n"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to extract text from EPUB: {str(e)}")
            
            if not text_content.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the EPUB.")
                
        else:
            # Assume it's a text file
            text_content = original_path.read_text(encoding="utf-8")
            
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File contains invalid UTF-8 encoding")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")
    
    # Validate extracted text
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="File contains no readable text content.")
    
    print(f"Extracted text length: {len(text_content)} characters")
    
    # Test Celery connection before queuing task
    try:
        # Quick health check
        health_task = tasks.health_check.delay()
        # Wait briefly to see if worker is responsive
        for _ in range(5):  # Wait up to 5 seconds
            if health_task.ready():
                break
            await asyncio.sleep(1)
        
        if not health_task.ready():
            print("Warning: Celery worker seems slow to respond")
        elif health_task.failed():
            raise Exception("Health check task failed")
            
    except Exception as e:
        print(f"Celery health check failed: {e}")
        raise HTTPException(status_code=503, detail="Task queue is not responding. Please try again later.")
    
    # Queue the TTS task
    try:
        result_task = tasks.convert_text_to_audio.delay(text_content, file_id)
        print(f"Task queued with ID: {result_task.id}")
    except Exception as e:
        print(f"Failed to queue TTS task: {e}")
        raise HTTPException(status_code=503, detail="Failed to queue conversion task. Please try again later.")
    
    # Return task info
    return {
        "file_id": file_id,
        "filename": original_path.name,
        "content_length": len(text_content),
        "task_id": result_task.id,
        "status": "processing",
        "message": "Text-to-speech conversion started. Use the task_id to check status."
    }


@api_router.get("/tasks/{task_id}")
async def task_status(task_id: str):
    """Return Celery task state + progress payload (if any)."""
    res = AsyncResult(task_id, app=celery_app)
    data = {"state": res.state}

    # SUCCESS / STARTED / PROGRESS etc. Progress is whatever your task puts there
    if res.info:
        # Expecting a dict like {"current": i, "total": n}
        data["progress"] = res.info

    if res.failed():
        data["error"] = str(res.info)

    return data


@api_router.get("/files/{file_id}/audio")
async def get_audio(file_id: str):
    """Return the audio file for download/streaming."""
    path = AUDIO_DIR / f"{file_id}.wav"
    if not path.exists():
        raise HTTPException(404, "Audio not ready")
    
    return FileResponse(
        path=str(path),
        media_type="audio/wav",
        filename=f"{file_id}.wav"
    )