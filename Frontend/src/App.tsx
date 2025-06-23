import React, { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [response, setResponse] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please select a file.");

    const formData = new FormData();
    formData.append('file', file);

    try {
      setIsUploading(true);
      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData
      });

      const result = await res.json();
      setResponse(result);
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="App">
      <h2>ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs</h2>
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={(e) => setFile(e.target.files[0])} />
        <input type="submit" value="Upload" />
      </form>
    </div>
  );
}

export default App;