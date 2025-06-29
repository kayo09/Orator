import os
import asyncio
from fastapi import FastAPI, File, UploadFile, HTTPException
import time
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import tempfile
import pdfplumber
from io import BytesIO
import subprocess
import pyclamd
import tasks
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware to handle CORS
ALLOWED_EXTENSIONS = {".pdf", ".epub"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/epub+zip"}
MAX_FILE_SIZE_MB = 30

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],  
    allow_headers=["*"],
)

CLAMD_HOST = os.getenv("CLAMD_HOST", "clamd")
CLAMD_PORT = int(os.getenv("CLAMD_PORT", 3310))
ENABLE_ANTIVIRUS = os.getenv("ENABLE_ANTIVIRUS", "true").lower() == "true"

async def get_clamd():
    host, port = CLAMD_HOST, CLAMD_PORT
    
    for attempt in range(10):
        try:
            cd = pyclamd.ClamdNetworkSocket(host=host, port=port)
            if cd.ping():
                return cd
        except (pyclamd.ConnectionError, ConnectionRefusedError, OSError) as e:
            print(f"Attempt {attempt + 1}: Could not connect to ClamAV at {host}:{port} - {e}")
            if attempt < 9:  # Don't sleep on the last attempt
                await asyncio.sleep(1)
    
    raise HTTPException(status_code=503, detail="Antivirus engine not available.")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")
    
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported MIME type.")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large.")
    
    # Only scan if antivirus is enabled
    if ENABLE_ANTIVIRUS:
        try:
            cd = await get_clamd()
            scan_result = cd.scan_stream(content)
            if scan_result:
                raise HTTPException(status_code=400, detail="Malware detected in uploaded file.")
        except HTTPException as e:
            if e.status_code == 503:
                print("Warning: ClamAV not available, skipping virus scan")
    else:
        print("Antivirus scanning disabled")
    
    text_content = ""
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
    
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")
    
    print(text_content)
    try:
        result_task = tasks.convert_text_to_audio.delay(text_content)
        # Return task ID or success response
    except Exception as e:
        # Log the error and return appropriate response
        print(f"Celery connection failed: {e}")
    # Handle synchronously or return error to client

    print(f"Task queued with ID: {result_task.id}")
    
    # Wait for the task to complete
    while not result_task.ready():
        time.sleep(1)
    
    if result_task.failed():
        raise HTTPException(status_code=500, detail="Audio conversion failed.")
    
    audio_path = result_task.result
    audio_url = f"/static/audio/{audio_path}"
    print(f"Audio file generated at: {audio_path}")
    
    return {"filename": file.filename, "content_length": len(content), "type": file.content_type, "audio_path": audio_url}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port="8000")