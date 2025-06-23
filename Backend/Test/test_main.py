import os
import sys
from fastapi.testclient import TestClient
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

client = TestClient(app)

def test_upload_file():
    test_file_path = os.path.join(os.path.dirname(__file__), "BookWhisper_7-Day_Roadmap.pdf")
    with open(test_file_path, "rb") as f:
        file_data = {"file": ("BookWhisper_7-Day_Roadmap.pdf", f, "application/pdf")}
        response = client.post("/upload", files=file_data)
        assert response.status_code == 200
        assert response.json()["filename"] == "BookWhisper_7-Day_Roadmap.pdf"

def test_invalid_extension():
    file_data = {"file": ("malware.exe", b"binary content", "application/octet-stream")}
    response = client.post("/upload", files=file_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file extension."

def test_invalid_mime_type():
    file_data = {"file": ("example.pdf", b"some data", "application/octet-stream")}
    response = client.post("/upload", files=file_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported MIME type."

def test_file_too_large():
    large_content = b"x" * (31 * 1024 * 1024)  # 31 MB
    file_data = {"file": ("large.pdf", large_content, "application/pdf")}
    response = client.post("/upload", files=file_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "File too large."

