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

app = FastAPI()

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

async def get_clamd():
    host, port = CLAMD_HOST, CLAMD_PORT
    
    for attempt in range(10):
        try:
            cd = pyclamd.ClamdNetworkSocket(host=host, port=port)
            if cd.ping():
                return cd
        except (pyclamd.ConnectionError, ConnectionRefusedError, OSError) as e:
            print(f"Attempt {attempt + 1}: Could not connect to ClamAV at {host}:{port} - {e}")
            if attempt < 9:
                await asyncio.sleep(1)
    
    raise HTTPException(status_code=503, detail="Antivirus engine not available.")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")
    
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported MIME type.")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large.")
    
    # Antivirus scan
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
    
    # Extract text from PDF
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
        result_task = tasks.convert_text_to_audio.delay(text_content)
        print(f"Task queued with ID: {result_task.id}")
    except Exception as e:
        print(f"Failed to queue TTS task: {e}")
        raise HTTPException(status_code=503, detail="Failed to queue conversion task. Please try again later.")
    # Return immediately with task info for polling
    return {
        "filename": file.filename, 
        "content_length": len(content), 
        "type": file.content_type, 
        "task_id": result_task.id,
        "status": "processing",
        "message": "Text-to-speech conversion started. Use the task_id to check status."
    }

@app.get("/download/{audio_filename}")
async def download_audio(audio_filename: str):
    """Download endpoint for audio files"""
    # Validate filename to prevent directory traversal
    if ".." in audio_filename or "/" in audio_filename or "\\" in audio_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Use consistent path construction
    audio_path = os.path.join("static", "audio", audio_filename)
    
    print(f"Download requested for: {audio_filename}")
    print(f"Looking for file at: {audio_path}")
    print(f"File exists: {os.path.exists(audio_path)}")
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Get file size for logging
    file_size = os.path.getsize(audio_path)
    print(f"File size: {file_size} bytes")
    
    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=audio_filename,
        headers={
            "Content-Disposition": f"attachment; filename={audio_filename}",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/stream/{audio_filename}")
async def stream_audio(audio_filename: str):
    """Streaming endpoint for audio files"""
    # Validate filename to prevent directory traversal
    if ".." in audio_filename or "/" in audio_filename or "\\" in audio_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    audio_path = os.path.join("static", "audio", audio_filename)
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=audio_filename
    )

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a TTS task with detailed information"""
    try:
        result_task = celery_app.AsyncResult(task_id)
        
        print(f"Checking task {task_id}: state={result_task.state}, status={result_task.status}")
        
        # Get detailed task info
        task_info = {
            "task_id": task_id,
            "state": result_task.state,
            "status": result_task.state.lower()
        }
        
        if result_task.state == 'PENDING':
            # Check if task actually exists
            try:
                inspect = celery_app.control.inspect()
                active_tasks = inspect.active()
                
                # Look for our task in active tasks
                task_found = False
                if active_tasks:
                    for worker, tasks in active_tasks.items():
                        for task in tasks:
                            if task.get('id') == task_id:
                                task_found = True
                                task_info["worker"] = worker
                                break
                
                if not task_found:
                    # Check if task is in queue
                    reserved_tasks = inspect.reserved()
                    if reserved_tasks:
                        for worker, tasks in reserved_tasks.items():
                            for task in tasks:
                                if task.get('id') == task_id:
                                    task_found = True
                                    task_info["worker"] = worker
                                    task_info["status"] = "queued"
                                    break
                
                if not task_found:
                    task_info["status"] = "unknown"
                    task_info["message"] = "Task not found in active or reserved queues"
                    
            except Exception as e:
                print(f"Error inspecting tasks: {e}")
                task_info["message"] = "Unable to get detailed task status"
                
            return task_info
            
        elif result_task.state == 'FAILURE':
            error_info = str(result_task.info) if result_task.info else "Unknown error"
            return {
                "status": "failed", 
                "task_id": task_id, 
                "error": error_info,
                "traceback": result_task.traceback
            }
            
        elif result_task.state == 'SUCCESS':
            audio_filename = result_task.result
            audio_path = os.path.join("static", "audio", audio_filename)
            
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "audio_url": f"/static/audio/{audio_filename}",
                    "download_url": f"/download/{audio_filename}",
                    "audio_filename": audio_filename,
                    "file_size": file_size
                }
            else:
                return {
                    "status": "processing", 
                    "task_id": task_id, 
                    "message": "Audio file is being written to disk"
                }
                
        elif result_task.state in ['PROGRESS', 'RETRY']:
            progress_info = result_task.info if result_task.info else {}
            return {
                "status": result_task.state.lower(),
                "task_id": task_id,
                "progress": progress_info
            }
        else:
            return {
                "status": result_task.state.lower(), 
                "task_id": task_id,
                "info": str(result_task.info) if result_task.info else None
            }
            
    except Exception as e:
        print(f"Error checking task {task_id}: {e}")
        return {
            "status": "error", 
            "task_id": task_id, 
            "error": f"Failed to get task status: {str(e)}"
        }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for the API and Celery"""
    health_status = {"api": "healthy"}
    
    try:
        # Test Celery connection
        inspect = celery_app.control.inspect()
        if inspect:
            stats = inspect.stats()
            if stats:
                health_status["celery"] = "healthy"
                health_status["workers"] = list(stats.keys())
            else:
                health_status["celery"] = "no_workers"
        else:
            health_status["celery"] = "unreachable"
    except Exception as e:
        health_status["celery"] = f"error: {str(e)}"
    
    # Check audio directory
    try:
        audio_dir = os.path.join("static", "audio")
        if os.path.exists(audio_dir) and os.access(audio_dir, os.W_OK):
            health_status["storage"] = "healthy"
        else:
            health_status["storage"] = "not_writable"
    except Exception as e:
        health_status["storage"] = f"error: {str(e)}"
    
    return health_status

# List available audio files (for debugging)
@app.get("/files")
async def list_files():
    audio_dir = os.path.join("static", "audio")
    if not os.path.exists(audio_dir):
        return {"files": [], "message": "Audio directory does not exist"}
    
    files = []
    try:
        for filename in os.listdir(audio_dir):
            filepath = os.path.join(audio_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "url": f"/static/audio/{filename}",
                    "download_url": f"/download/{filename}"
                })
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x["created"], reverse=True)
        
    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}", "files": []}
    
    return {"files": files, "count": len(files)}

# Debug endpoint for Celery workers
@app.get("/workers")
async def get_worker_info():
    """Get information about Celery workers"""
    try:
        inspect = celery_app.control.inspect()
        
        if not inspect:
            return {"error": "Cannot connect to Celery"}
        
        info = {}
        
        # Get worker stats
        stats = inspect.stats()
        if stats:
            info["stats"] = stats
        
        # Get active tasks
        active = inspect.active()
        if active:
            info["active_tasks"] = active
        
        # Get reserved tasks
        reserved = inspect.reserved()
        if reserved:
            info["reserved_tasks"] = reserved
        
        # Get registered tasks
        registered = inspect.registered()
        if registered:
            info["registered_tasks"] = registered
        
        return info
        
    except Exception as e:
        return {"error": f"Failed to get worker info: {str(e)}"}

# Test endpoint for quick TTS test
@app.post("/test-tts")
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