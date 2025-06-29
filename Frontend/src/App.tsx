import { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a file.");
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        alert(`Error: ${errorData.detail || 'Upload failed'}`);
        return;
      }

      const result = await res.json();
      console.log(result);
      setAudioUrl(`http://localhost:8000${result.audio_url}`);
    } catch (error) {
      console.error('Upload error:', error);
      alert('An error occurred during upload.');
    }
  };

  return (
    <div className="App">
      <h2>ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,.epub"
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            setFile(e.target.files?.[0] ?? null)
          }
        />
        <input type="submit" value="Upload" />
      </form>

      {audioUrl && (
        <div>
          <h3>Your Audio:</h3>
          <audio controls src={audioUrl}>
            Your browser does not support the audio element.
          </audio>
        </div>
      )}
    </div>
  );
}

export default App;
