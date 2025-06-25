import { useState } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState<File | null>(null);

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
      const result = await res.json();
      console.log(result);
    } catch (error) {
      console.error('Upload error:', error);
    }
  };

  return (
    <div className="App">
      <h2>ORATOR 🗣️ : THE ONLY WAY TO LISTEN TO PDFs AND EPUBs</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            setFile(e.target.files?.[0] ?? null)
          }
        />
        <input type="submit" value="Upload" />
      </form>
    </div>
  );
}

export default App;
