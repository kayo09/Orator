import React, { useState } from 'react';

function App() {
  const [file, setFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('http://localhost:8000/upload', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      alert('Upload successful!');
    } else {
      alert('Upload failed.');
    }
  };

  return (
    <div>
      <h2>Upload a File</h2>
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={(e) => setFile(e.target.files[0])} />
        <input type="submit" value="Upload" />
      </form>
    </div>
  );
}

export default App;
