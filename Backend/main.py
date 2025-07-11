import os
import asyncio
from fastapi import FastAPI, File, UploadFile, HTTPException
import time
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pdfplumber
from io import BytesIO
import subprocess
import pyclamd
import tasks  
from fastapi.staticfiles import StaticFiles
from celery_config import celery_app
from router import api_router          

app = FastAPI()
app.include_router(api_router, prefix="/api")   

# Create static directory if it doesn't exist
os.makedirs("static/audio", exist_ok=True)

# Mount static files - this will serve audio files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware to handle CORS
ALLOWED_EXTENSIONS = {".pdf", ".epub"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/epub+zip"}
MAX_FILE_SIZE_MB = 30

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

CLAMD_HOST = os.getenv("CLAMD_HOST", "clamd")
CLAMD_PORT = int(os.getenv("CLAMD_PORT", 3310))
ENABLE_ANTIVIRUS = os.getenv("ENABLE_ANTIVIRUS", "true").lower() == "true"

async def test_tts():
    """Test TTS with a short text"""
    try:
        test_text = "Hello, this is a test of the text to speech system. If you can hear this, everything is working correctly."
        result_task = tasks.convert_text_to_audio.delay(test_text)
        
        return {
            "message": "Test TTS task queued",
            "task_id": result_task.id,
            "test_text": test_text
        }
        
    except Exception as e:
        return {"error": f"Failed to queue test task: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)