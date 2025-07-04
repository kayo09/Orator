import { useState, useRef } from "react";
import "./App.css";

/**************************************************
 * Types
 *************************************************/
interface TaskStatusResponse {
  state: "PENDING" | "STARTED" | "PROGRESS" | "SUCCESS" | "FAILURE";
  progress?: { current: number; total: number };
  error?: string;
}

interface UploadState {
  fileId: string;
  taskId: string;
  originalName: string;
  status: "uploading" | "converting" | "completed" | "failed";
  progress?: number; // percent 0–100
  error?: string;
}

/**************************************************
 * Constants
 *************************************************/
// Prefer an env var so dev/production can differ
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const routes = {
  upload: () => `${API_BASE_URL}/api/files`,
  convert: (fileId: string) => `${API_BASE_URL}/api/tasks?file_id=${fileId}`,
  task: (taskId: string) => `${API_BASE_URL}/api/tasks/${taskId}`,
  audio: (fileId: string) => `${API_BASE_URL}/api/files/${fileId}/audio`,
};

/**************************************************
 * Component
 *************************************************/
export default function App() {
  /********** Local state **********/
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<UploadState | null>(null);
  const [debug, setDebug] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);

  /********** Helpers **********/
  const log = (msg: string) => setDebug((d) => `${msg}\n${d}`);

  /********** Upload + convert **********/
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    // reset UI
    setUpload(null);
    setDebug("");

    try {
      /* 1️⃣ Upload file */
      log("Uploading file …");
      const formData = new FormData();
      formData.append("file", file);

      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const upRes = await fetch(routes.upload(), {
        method: "POST",
        body: formData,
        signal: abortRef.current.signal,
      });
      if (!upRes.ok) throw new Error(`Upload failed: ${upRes.status}`);
      const { file_id }: { file_id: string } = await upRes.json();

      /* 2️⃣ Start conversion */
      log("File stored – queueing TTS task …");
      const cvRes = await fetch(routes.convert(file_id), {
        method: "POST",
        signal: abortRef.current.signal,
      });
      if (!cvRes.ok) throw new Error(`Start convert failed: ${cvRes.status}`);
      const { task_id }: { task_id: string } = await cvRes.json();

      /* 3️⃣ Initialise UI state */
      setUpload({
        fileId: file_id,
        taskId: task_id,
        originalName: file.name,
        status: "converting",
      });

      /* 4️⃣ Poll status */
      pollTask(task_id, file_id);
    } catch (err) {
      console.error(err);
      log(String(err));
      setUpload({
        fileId: "",
        taskId: "",
        originalName: file.name,
        status: "failed",
        error: String(err),
      });
    }
  }

  /********** Poll helper **********/
  const pollTask = async (taskId: string, fileId: string) => {
    let attempts = 0;
    const MAX_ATTEMPTS = 120; // ~10 min @ 5 s

    const poll = async () => {
      attempts++;
      try {
        const res = await fetch(routes.task(taskId));
        if (!res.ok) throw new Error("status check failed");
        const data: TaskStatusResponse = await res.json();

        if (data.state === "SUCCESS") {
          setUpload((u) =>
            u && u.taskId === taskId
              ? { ...u, status: "completed", progress: 100 }
              : u
          );
          log("Conversion completed ✔️");
          return;
        }

        if (data.state === "FAILURE") {
          setUpload((u) =>
            u && u.taskId === taskId
              ? { ...u, status: "failed", error: data.error }
              : u
          );
          log(`Conversion failed: ${data.error}`);
          return;
        }

        if (data.progress) {
          const pct = Math.round((data.progress.current / data.progress.total) * 100);
          setUpload((u) => (u ? { ...u, progress: pct } : u));
        }

        if (attempts < MAX_ATTEMPTS) setTimeout(poll, 5000);
        else {
          setUpload((u) => (u ? { ...u, status: "failed", error: "Timed out" } : u));
          log("Timed out waiting for conversion");
        }
      } catch (err) {
        log(`Polling error: ${err}`);
        if (attempts < MAX_ATTEMPTS) setTimeout(poll, 5000);
        else setUpload((u) => (u ? { ...u, status: "failed", error: String(err) } : u));
      }
    };

    poll();
  };

  /********** UI **********/
  const isBusy = upload && ["uploading", "converting"].includes(upload.status);

  return (
    <div className="App">
      <h2>ORATOR 🗣️ : Listen to PDFs & EPUBs</h2>

      {/* Upload form */}
      <form onSubmit={handleSubmit} style={{ marginBlockEnd: "1rem" }}>
        <input
          type="file"
          accept=".pdf,.epub"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          disabled={isBusy}
        />
        <button type="submit" disabled={!file || isBusy} style={{ marginInlineStart: 8 }}>
          {isBusy ? "Working…" : "Upload"}
        </button>
      </form>

      {/* Progress */}
      {upload && (upload.status === "converting" || upload.status === "uploading") && (
        <section style={{ width: "100%", maxWidth: 400 }}>
          <p>Converting… {upload.progress ?? 0}%</p>
          <progress value={upload.progress ?? 0} max={100} style={{ width: "100%" }} />
        </section>
      )}

      {/* Completed */}
      {upload && upload.status === "completed" && (
        <section style={{ marginTop: 24 }}>
          <h3>Your audio is ready!</h3>
          <audio
            controls
            src={routes.audio(upload.fileId)}
            style={{ width: "100%", maxWidth: 500 }}
          />
          <div style={{ marginTop: 8 }}>
            <a href={routes.audio(upload.fileId)} download={`${upload.originalName}.wav`}>
              Download
            </a>
          </div>
        </section>
      )}

      {/* Error */}
      {upload && upload.status === "failed" && (
        <p style={{ color: "red" }}>⚠️ {upload.error}</p>
      )}

      {/* Debug */}
      {debug && (
        <pre
          style={{
            marginTop: 24,
            background: "#f4f4f4",
            padding: 12,
            borderRadius: 4,
            maxHeight: 200,
            overflowY: "auto",
            fontSize: 12,
          }}
        >
          {debug}
        </pre>
      )}
    </div>
  );
}
