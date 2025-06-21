import os
from fastapi import FastAPI, File, UploadFile, HTTPException
import time
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import pyclamd

app = FastAPI()
# Middleware to handle CORS

ALLOWED_EXTENSIONS = {".pdf", ".epub"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/epub+zip"}
MAX_FILE_SIZE_MB = 30

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    cd = pyclamd.ClamdNetworkSocket(host="localhost", port=3310)
    if not cd.ping():
        raise HTTPException(status_code=500, detail="Antivirus engine not available.")

    if cd.scan_stream(content):
        raise HTTPException(status_code=400, detail="Malware detected in uploaded file.")


    return {"filename": file.filename, "content_length": len(content), "type": file.content_type}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.1", port=8000)
