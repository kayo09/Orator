import { useState } from 'react';
import './App.css';

interface UploadResponse {
  filename: string;
  content_length: number;
  type: string;
  audio_url?: string;
  download_url?: string;
  task_id: string;
  status: string;
  message?: string;
}

interface TaskStatusResponse {
  status: string;
  task_id: string;
  audio_url?: string;
  download_url?: string;
  error?: string;
}

// Configure your backend URL here
const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [debugInfo, setDebugInfo] = useState<string>('');

  const handleDownload = async () => {
    if (!uploadResponse?.download_url) {
      alert('Download URL not available');
      return;
    }

    try {
      setDebugInfo('Starting download...');
      
      // Method 1: Direct fetch and blob download (recommended)
      const response = await fetch(`${API_BASE_URL}${uploadResponse.download_url}`, {
        method: 'GET',
        mode: 'cors',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = uploadResponse.filename.replace(/\.[^/.]+$/, ".wav");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up
      window.URL.revokeObjectURL(url);
      setDebugInfo('Download completed successfully!');
      
    } catch (error) {
      console.error('Download error:', error);
      setDebugInfo(`Download failed: ${error}`);
      
      // Fallback: Try opening in new window
      try {
        const fallbackUrl = `${API_BASE_URL}${uploadResponse.download_url}`;
        window.open(fallbackUrl, '_blank');
        setDebugInfo('Opened download in new window (fallback method)');
      } catch (fallbackError) {
        alert(`Download failed: ${error}`);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a file.");
      return;
    }

    setIsUploading(true);
    setUploadResponse(null);
    setDebugInfo('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      setDebugInfo('Uploading file...');
      
      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
        mode: 'cors',
      });

      if (!res.ok) {
        const errorData = await res.json();
        alert(`Error: ${errorData.detail || 'Upload failed'}`);
        return;
      }

      const result: UploadResponse = await res.json();
      console.log('Upload result:', result);
      setUploadResponse(result);
      setDebugInfo(`Upload successful. Status: ${result.status}`);

      // If status is processing, start polling
      if (result.status === 'processing') {
        pollTaskStatus(result.task_id);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setDebugInfo(`Upload error: ${error}`);
      alert('An error occurred during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    setIsPolling(true);
    const maxAttempts = 200; // Poll for up to 5 minutes (60 * 5 seconds)
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        setDebugInfo(`Checking conversion status... (attempt ${attempts + 1}/${maxAttempts})`);
        
        const res = await fetch(`${API_BASE_URL}/task/${taskId}`, {
          mode: 'cors',
        });
        
        if (!res.ok) {
          throw new Error('Failed to check task status');
        }

        const taskStatus: TaskStatusResponse = await res.json();
        console.log('Task status:', taskStatus);
        
        if (taskStatus.status === 'completed' && taskStatus.audio_url) {
          setUploadResponse(prev => prev ? {
            ...prev,
            audio_url: taskStatus.audio_url!,
            download_url: taskStatus.download_url!,
            status: 'completed'
          } : null);
          setIsPolling(false);
          setDebugInfo('Conversion completed successfully!');
          return;
        } else if (taskStatus.status === 'failed') {
          alert(`Audio conversion failed: ${taskStatus.error || 'Unknown error'}`);
          setIsPolling(false);
          setDebugInfo(`Conversion failed: ${taskStatus.error || 'Unknown error'}`);
          return;
        } else if (taskStatus.status === 'pending' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          alert('Audio conversion timed out. Please try again.');
          setIsPolling(false);
          setDebugInfo('Conversion timed out');
        }
      } catch (error) {
        console.error('Error polling task status:', error);
        setDebugInfo(`Polling error: ${error}`);
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 5000);
        } else {
          alert('Failed to check conversion status. Please try again.');
          setIsPolling(false);
        }
      }
    };

    poll();
  };

  // Debug function to check available files
  const checkFiles = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/files`);
      const data = await res.json();
      console.log('Available files:', data);
      setDebugInfo(`Found ${data.count} files in audio directory`);
    } catch (error) {
      console.error('Error checking files:', error);
      setDebugInfo(`Error checking files: ${error}`);
    }
  };

  return (
    <div className="App">
      <h2>ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs</h2>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <input
            type="file"
            accept=".pdf,.epub"
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setFile(e.target.files?.[0] ?? null)
            }
            disabled={isUploading}
          />
        </div>
        
        <input 
          type="submit" 
          value={isUploading ? "Processing..." : "Upload"} 
          disabled={isUploading || !file}
        />
      </form>

      {/* Debug section */}
      <div style={{ marginTop: '20px' }}>
        <button onClick={checkFiles} style={{ marginRight: '10px' }}>
          🔍 Check Available Files
        </button>
        {debugInfo && (
          <div style={{ 
            marginTop: '10px', 
            padding: '10px', 
            backgroundColor: '#f0f0f0', 
            borderRadius: '5px',
            fontSize: '12px',
            fontFamily: 'monospace'
          }}>
            Debug: {debugInfo}
          </div>
        )}
      </div>

      {(isUploading || isPolling) && (
        <div style={{ marginTop: '20px' }}>
          <p>
            {isUploading ? 'Uploading your document...' : 'Converting your document to audio... This may take a few minutes.'}
          </p>
          <div style={{ 
            width: '100%', 
            height: '4px', 
            backgroundColor: '#e0e0e0', 
            borderRadius: '2px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: '100%',
              height: '100%',
              backgroundColor: '#007bff',
              animation: 'loading 2s infinite'
            }}></div>
          </div>
        </div>
      )}

      {uploadResponse && (
        <div style={{ marginTop: '30px' }}>
          {uploadResponse.status === 'completed' ? (
            <>
              <h3>Your Audio is Ready! 🎵</h3>
              
              <div style={{ marginBottom: '20px' }}>
                <p><strong>Original File:</strong> {uploadResponse.filename}</p>
                <p><strong>File Size:</strong> {(uploadResponse.content_length / 1024 / 1024).toFixed(2)} MB</p>
                <p><strong>Status:</strong> {uploadResponse.status}</p>
              </div>

              {/* Audio Player */}
              {uploadResponse.audio_url && (
                <div style={{ marginBottom: '20px' }}>
                  <h4>Listen Online:</h4>
                  <audio 
                    controls 
                    src={`${API_BASE_URL}${uploadResponse.audio_url}`}
                    style={{ width: '100%', maxWidth: '500px' }}
                  >
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}

              {/* Download Buttons */}
              {uploadResponse.download_url && (
                <div style={{ marginBottom: '20px' }}>
                  <button 
                    onClick={handleDownload}
                    style={{
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      padding: '10px 20px',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      fontSize: '16px',
                      marginRight: '10px'
                    }}
                  >
                    📥 Download Audio File
                  </button>
                  
                  {/* Alternative download link */}
                  <a 
                    href={`${API_BASE_URL}${uploadResponse.download_url}`}
                    download={uploadResponse.filename.replace(/\.[^/.]+$/, ".wav")}
                    style={{
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      padding: '10px 20px',
                      borderRadius: '5px',
                      textDecoration: 'none',
                      fontSize: '16px'
                    }}
                  >
                    🔗 Direct Download Link
                  </a>
                </div>
              )}
              
              {/* URLs for debugging */}
              <details style={{ marginTop: '20px' }}>
                <summary style={{ cursor: 'pointer' }}>🛠️ Debug Information</summary>
                <div style={{ 
                  marginTop: '10px', 
                  padding: '10px', 
                  backgroundColor: '#f8f9fa', 
                  borderRadius: '5px',
                  fontSize: '12px',
                  fontFamily: 'monospace'
                }}>
                  <p><strong>Audio URL:</strong> {API_BASE_URL}{uploadResponse.audio_url}</p>
                  <p><strong>Download URL:</strong> {API_BASE_URL}{uploadResponse.download_url}</p>
                  <p><strong>Task ID:</strong> {uploadResponse.task_id}</p>
                </div>
              </details>
            </>
          ) : (
            <>
              <h3>Processing Your Document... ⏳</h3>
              <div style={{ marginBottom: '20px' }}>
                <p><strong>Original File:</strong> {uploadResponse.filename}</p>
                <p><strong>File Size:</strong> {(uploadResponse.content_length / 1024 / 1024).toFixed(2)} MB</p>
                <p><strong>Status:</strong> {uploadResponse.status}</p>
                {uploadResponse.message && <p><strong>Message:</strong> {uploadResponse.message}</p>}
              </div>
              {isPolling && <p>🔄 Checking conversion status...</p>}
            </>
          )}
        </div>
      )}

      <style>{`
        @keyframes loading {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}

export default App;