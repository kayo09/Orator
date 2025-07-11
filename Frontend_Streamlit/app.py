import streamlit as st
import requests
import time
import os
import json
from typing import Dict, Any, Optional, List
import base64

# Configure page
st.set_page_config(
    page_title="ORATOR 🗣️",
    page_icon="🗣️",
    layout="wide"
)

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class APIRoutes:
    @staticmethod
    def upload():
        return f"{API_BASE_URL}/api/files"
    
    @staticmethod
    def convert(file_id: str):
        return f"{API_BASE_URL}/api/tasks?file_id={file_id}"
    
    @staticmethod
    def task(task_id: str):
        return f"{API_BASE_URL}/api/tasks/{task_id}"
    
    @staticmethod
    def audio(file_id: str):
        return f"{API_BASE_URL}/api/files/{file_id}/audio"
    
    @staticmethod
    def text_segments(file_id: str):
        return f"{API_BASE_URL}/api/files/{file_id}/segments"
    
    @staticmethod
    def pdf_content(file_id: str):
        return f"{API_BASE_URL}/api/files/{file_id}/pdf"

# Initialize session state
if 'upload_state' not in st.session_state:
    st.session_state.upload_state = None
if 'debug_logs' not in st.session_state:
    st.session_state.debug_logs = []
if 'conversion_complete' not in st.session_state:
    st.session_state.conversion_complete = False
if 'text_segments' not in st.session_state:
    st.session_state.text_segments = []
if 'current_segment' not in st.session_state:
    st.session_state.current_segment = 0
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'audio_position' not in st.session_state:
    st.session_state.audio_position = 0
if 'file_type' not in st.session_state:
    st.session_state.file_type = None

def log_debug(message: str):
    """Add debug message to logs"""
    st.session_state.debug_logs.insert(0, message)
    # Keep only last 10 logs
    if len(st.session_state.debug_logs) > 10:
        st.session_state.debug_logs = st.session_state.debug_logs[:10]

def upload_file(file) -> Optional[str]:
    """Upload file to server and return file_id"""
    try:
        log_debug("Uploading file...")
        
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(APIRoutes.upload(), files=files)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("file_id")
        else:
            st.error(f"Upload failed: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        log_debug(f"Upload error: {str(e)}")
        return None

def start_conversion(file_id: str) -> Optional[str]:
    """Start conversion task and return task_id"""
    try:
        log_debug("File stored – queueing TTS task...")
        
        response = requests.post(APIRoutes.convert(file_id))
        
        if response.status_code == 200:
            data = response.json()
            return data.get("task_id")
        else:
            st.error(f"Start convert failed: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Conversion start error: {str(e)}")
        log_debug(f"Conversion start error: {str(e)}")
        return None

def check_task_status(task_id: str) -> Dict[str, Any]:
    """Check task status"""
    try:
        response = requests.get(APIRoutes.task(task_id))
        if response.status_code == 200:
            return response.json()
        else:
            return {"state": "FAILURE", "error": f"Status check failed: {response.status_code}"}
    except Exception as e:
        return {"state": "FAILURE", "error": str(e)}

def fetch_text_segments(file_id: str) -> List[Dict]:
    """Fetch text segments with timestamps for read-along"""
    try:
        response = requests.get(APIRoutes.text_segments(file_id))
        if response.status_code == 200:
            return response.json().get("segments", [])
        else:
            log_debug(f"Failed to fetch segments: {response.status_code}")
            return []
    except Exception as e:
        log_debug(f"Error fetching segments: {str(e)}")
        return []

def fetch_pdf_content(file_id: str) -> Optional[bytes]:
    """Fetch PDF content for display"""
    try:
        response = requests.get(APIRoutes.pdf_content(file_id))
        if response.status_code == 200:
            return response.content
        else:
            log_debug(f"Failed to fetch PDF: {response.status_code}")
            return None
    except Exception as e:
        log_debug(f"Error fetching PDF: {str(e)}")
        return None

def poll_task_status(task_id: str, file_id: str, progress_bar, status_text):
    """Poll task status with progress updates"""
    max_attempts = 120  # ~10 min @ 5s intervals
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        
        # Check task status
        status_data = check_task_status(task_id)
        
        if status_data["state"] == "SUCCESS":
            progress_bar.progress(100)
            status_text.success("Conversion completed ✔️")
            log_debug("Conversion completed ✔️")
            
            # Fetch text segments for read-along
            segments = fetch_text_segments(file_id)
            st.session_state.text_segments = segments
            
            st.session_state.conversion_complete = True
            st.session_state.upload_state = {
                "file_id": file_id,
                "task_id": task_id,
                "status": "completed"
            }
            st.rerun()
            return
            
        elif status_data["state"] == "FAILURE":
            error_msg = status_data.get("error", "Unknown error")
            status_text.error(f"Conversion failed: {error_msg}")
            log_debug(f"Conversion failed: {error_msg}")
            st.session_state.upload_state = {
                "file_id": file_id,
                "task_id": task_id,
                "status": "failed",
                "error": error_msg
            }
            st.rerun()
            return
            
        elif status_data.get("progress"):
            current = status_data["progress"]["current"]
            total = status_data["progress"]["total"]
            progress_pct = int((current / total) * 100)
            progress_bar.progress(progress_pct)
            status_text.info(f"Converting... {progress_pct}%")
        
        time.sleep(5)
    
    # Timeout
    status_text.error("Timed out waiting for conversion")
    log_debug("Timed out waiting for conversion")
    st.session_state.upload_state = {
        "file_id": file_id,
        "task_id": task_id,
        "status": "failed",
        "error": "Timed out"
    }
    st.rerun()

def render_text_segments():
    """Render text segments with highlighting"""
    if not st.session_state.text_segments:
        st.info("No text segments available for read-along")
        return
    
    st.subheader("Read Along")
    
    # Audio controls
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("⏪ Previous"):
            if st.session_state.current_segment > 0:
                st.session_state.current_segment -= 1
                st.rerun()
    
    with col2:
        if st.button("⏩ Next"):
            if st.session_state.current_segment < len(st.session_state.text_segments) - 1:
                st.session_state.current_segment += 1
                st.rerun()
    
    with col3:
        segment_num = st.slider(
            "Go to segment",
            min_value=0,
            max_value=len(st.session_state.text_segments) - 1,
            value=st.session_state.current_segment,
            key="segment_slider"
        )
        if segment_num != st.session_state.current_segment:
            st.session_state.current_segment = segment_num
            st.rerun()
    
    # Display segments with highlighting
    st.markdown("### Text Content")
    
    for i, segment in enumerate(st.session_state.text_segments):
        if i == st.session_state.current_segment:
            # Highlight current segment
            st.markdown(
                f"""
                <div style="background-color: #ffeb3b; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <strong>🔊 Currently Reading:</strong><br>
                    {segment.get('text', '')}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Regular segment
            st.markdown(
                f"""
                <div style="background-color: #f5f5f5; padding: 8px; border-radius: 3px; margin: 3px 0;">
                    {segment.get('text', '')}
                </div>
                """,
                unsafe_allow_html=True
            )

def render_pdf_viewer(file_id: str):
    """Render PDF viewer"""
    pdf_content = fetch_pdf_content(file_id)
    
    if pdf_content:
        # Convert PDF to base64 for display
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Create PDF viewer
        st.markdown("### PDF Document")
        st.markdown(
            f"""
            <iframe
                src="data:application/pdf;base64,{pdf_base64}"
                width="100%"
                height="600px"
                style="border: 1px solid #ddd; border-radius: 5px;"
            >
            </iframe>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning("PDF content not available for viewing")

def main():
    st.title("ORATOR 🗣️ : Listen to PDFs & EPUBs")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF or EPUB file",
        type=['pdf', 'epub'],
        help="Upload a PDF or EPUB file to convert to audio with read-along feature"
    )
    
    if uploaded_file is not None:
        st.session_state.file_type = uploaded_file.type
    
    # Upload and convert button
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Upload & Convert", type="primary"):
                # Reset state
                st.session_state.upload_state = None
                st.session_state.conversion_complete = False
                st.session_state.debug_logs = []
                st.session_state.text_segments = []
                st.session_state.current_segment = 0
                
                # Upload file
                file_id = upload_file(uploaded_file)
                
                if file_id:
                    # Start conversion
                    task_id = start_conversion(file_id)
                    
                    if task_id:
                        st.session_state.upload_state = {
                            "file_id": file_id,
                            "task_id": task_id,
                            "status": "converting",
                            "original_name": uploaded_file.name
                        }
                        st.rerun()
    
    # Show conversion progress
    if st.session_state.upload_state and st.session_state.upload_state["status"] == "converting":
        st.subheader("Converting...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Start polling in the background
        with st.spinner("Converting your file..."):
            poll_task_status(
                st.session_state.upload_state["task_id"],
                st.session_state.upload_state["file_id"],
                progress_bar,
                status_text
            )
    
    # Show completed conversion with read-along
    if st.session_state.upload_state and st.session_state.upload_state["status"] == "completed":
        st.success("🎉 Your audio is ready!")
        
        file_id = st.session_state.upload_state["file_id"]
        original_name = st.session_state.upload_state.get("original_name", "audio")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["🎵 Audio Player", "📖 Read Along", "📄 Document View"])
        
        with tab1:
            # Audio player
            audio_url = APIRoutes.audio(file_id)
            
            try:
                # Fetch audio file
                response = requests.get(audio_url)
                if response.status_code == 200:
                    st.audio(response.content, format='audio/wav')
                    
                    # Download button
                    st.download_button(
                        label="Download Audio File",
                        data=response.content,
                        file_name=f"{original_name}.wav",
                        mime="audio/wav"
                    )
                else:
                    st.error("Failed to load audio file")
                    
            except Exception as e:
                st.error(f"Error loading audio: {str(e)}")
        
        with tab2:
            # Read-along interface
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Audio player for read-along
                try:
                    response = requests.get(audio_url)
                    if response.status_code == 200:
                        st.markdown("#### Audio Control")
                        st.audio(response.content, format='audio/wav')
                    else:
                        st.error("Failed to load audio file")
                except Exception as e:
                    st.error(f"Error loading audio: {str(e)}")
            
            with col2:
                # Segment info
                if st.session_state.text_segments:
                    current_segment = st.session_state.text_segments[st.session_state.current_segment]
                    st.markdown("#### Current Segment Info")
                    st.info(f"Segment {st.session_state.current_segment + 1} of {len(st.session_state.text_segments)}")
                    
                    # Show timestamp if available
                    if 'start_time' in current_segment:
                        st.text(f"Start: {current_segment['start_time']:.2f}s")
                    if 'end_time' in current_segment:
                        st.text(f"End: {current_segment['end_time']:.2f}s")
            
            # Render text segments
            render_text_segments()
        
        with tab3:
            # Document viewer (PDF only)
            if st.session_state.file_type == "application/pdf":
                render_pdf_viewer(file_id)
            else:
                st.info("Document preview is only available for PDF files.")
                
                # Show EPUB content as text segments instead
                if st.session_state.text_segments:
                    st.markdown("### EPUB Content")
                    for i, segment in enumerate(st.session_state.text_segments):
                        st.markdown(f"**Segment {i+1}:**")
                        st.write(segment.get('text', ''))
                        st.markdown("---")
    
    # Show error
    if st.session_state.upload_state and st.session_state.upload_state["status"] == "failed":
        error_msg = st.session_state.upload_state.get("error", "Unknown error")
        st.error(f"⚠️ {error_msg}")
        
        # Reset button
        if st.button("Try Again"):
            st.session_state.upload_state = None
            st.session_state.conversion_complete = False
            st.session_state.text_segments = []
            st.session_state.current_segment = 0
            st.rerun()
    
    # Debug logs (collapsible)
    if st.session_state.debug_logs:
        with st.expander("Debug Logs"):
            for log in st.session_state.debug_logs:
                st.text(log)
    
    # Sidebar controls
    st.sidebar.header("Controls")
    
    # Clear state button
    if st.sidebar.button("Clear State"):
        st.session_state.upload_state = None
        st.session_state.conversion_complete = False
        st.session_state.debug_logs = []
        st.session_state.text_segments = []
        st.session_state.current_segment = 0
        st.rerun()
    
    # Settings
    if st.sidebar.button("Refresh Segments"):
        if st.session_state.upload_state and st.session_state.upload_state["status"] == "completed":
            file_id = st.session_state.upload_state["file_id"]
            segments = fetch_text_segments(file_id)
            st.session_state.text_segments = segments
            st.rerun()

if __name__ == "__main__":
    main()