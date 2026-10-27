
import { useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const languages = [
  { code: "English", name: "English" },
  { code: "Telugu", name: "Telugu" },
  { code: "Hindi", name: "Hindi" },
  { code: "Tamil", name: "Tamil" },
  { code: "Kannada", name: "Kannada" },
  { code: "Malayalam", name: "Malayalam" },
  { code: "Bengali", name: "Bengali" },
  { code: "Marathi", name: "Marathi" },
  { code: "Gujarati", name: "Gujarati" },
  { code: "Punjabi", name: "Punjabi" },
  { code: "Odia", name: "Odia" },
];

export default function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [source, setSource] = useState("English");
  const [target, setTarget] = useState("Telugu");
  const [fileId, setFileId] = useState("");
  const [uploadInfo, setUploadInfo] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle");

  const busy = status === "uploading" || status === "dubbing";

  function selectFile(selectedFile) {
    if (!selectedFile) return;

    const allowedExtensions = [".mp4", ".mov", ".mkv", ".webm"];
    const extension = selectedFile.name
      .slice(selectedFile.name.lastIndexOf("."))
      .toLowerCase();

    if (!allowedExtensions.includes(extension)) {
      setError("Please select an MP4, MOV, MKV, or WEBM video.");
      return;
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      setError("Video size must be less than 100 MB.");
      return;
    }

    setFile(selectedFile);
    setFileId("");
    setUploadInfo(null);
    setResult(null);
    setError("");
    setStatus("idle");
  }

  async function readError(response) {
    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        return data.detail;
      }

      return JSON.stringify(data.detail || data);
    } catch {
      return `Request failed with status ${response.status}.`;
    }
  }

  async function createDub() {
    if (!file) {
      setError("Please select a video before starting dubbing.");
      return;
    }

    if (busy) return;

    setError("");
    setResult(null);
    setUploadInfo(null);
    setStatus("uploading");

    let currentFileId = fileId;

    try {
      // Step 1: Upload the video.
      if (!currentFileId) {
        const formData = new FormData();
        formData.append("file", file);

        const uploadResponse = await fetch(`${API_URL}/upload`, {
          method: "POST",
          body: formData,
        });

        if (!uploadResponse.ok) {
          throw new Error(await readError(uploadResponse));
        }

        const uploadData = await uploadResponse.json();

        if (!uploadData.file_id) {
          throw new Error(
            "Upload succeeded but the server did not return a file ID."
          );
        }

        currentFileId = uploadData.file_id;
        setFileId(currentFileId);
        setUploadInfo(uploadData);
      }

      // Step 2: Request transcription, translation and dubbing.
      setStatus("dubbing");

      const dubResponse = await fetch(
        `${API_URL}/dub/${encodeURIComponent(currentFileId)}?target_language=${encodeURIComponent(target)}`,
        { method: "POST" }
      );

      if (!dubResponse.ok) {
        throw new Error(await readError(dubResponse));
      }

      const dubData = await dubResponse.json();

      setResult(dubData);
      setStatus("success");
    } catch (err) {
      console.error("VoxDub AI request failed:", err);

      if (
        err instanceof TypeError ||
        String(err.message).includes("Failed to fetch")
      ) {
        setError(
          "Could not connect to the backend. Check that FastAPI is running at http://127.0.0.1:8000."
        );
      } else {
        setError(err.message || "Something went wrong while dubbing.");
      }

      setStatus("error");
    }
  }

  async function downloadFile(endpoint, filename) {
    if (!fileId) {
      setError("No uploaded video is available. Please upload again.");
      return;
    }

    try {
      setError("");

      const response = await fetch(
        `${API_URL}${endpoint}/${encodeURIComponent(fileId)}`
      );

      if (!response.ok) {
        throw new Error(await readError(response));
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = objectUrl;
      link.download = filename;

      document.body.appendChild(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      console.error("Download failed:", err);
      setError(err.message || "Download failed.");
    }
  }

  const sourceName =
    languages.find((language) => language.code === source)?.name || source;

  const targetName =
    languages.find((language) => language.code === target)?.name || target;

  return (
    <div className="app">
      <main className="main content">
        <header className="hero">
          <div className="hero-copy">
            <span className="eyebrow">✦ AI VIDEO TRANSLATION STUDIO</span>

            <h1>
              Your videos.
              <br />
              <span>Every language.</span>
            </h1>

            <p>
              Translate and dub your videos into regional languages with an
              AI-powered workflow.
            </p>
          </div>

          <div className="hero-art" aria-hidden="true">
            <div className="language-art">
              <span>文</span>
              <span>A</span>
              <small>EN → TE</small>
            </div>
          </div>
        </header>

        <section className="section-heading">
          <div>
            <h2>Create a dubbing project</h2>
            <p>Upload a video, select a language and create your dub.</p>
          </div>

          <span className="step-badge">STEP 01 / 03</span>
        </section>

        <section className="workspace-grid">
          <div className="panel upload-panel">
            <div className="panel-heading">
              <span className="icon-box">⇧</span>

              <div>
                <h3>Upload your video</h3>
                <p>Choose the video you want to dub.</p>
              </div>
            </div>

            <button
              type="button"
              className="dropzone"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
            >
              <span className="upload-icon">⇧</span>

              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>
                    {(file.size / (1024 * 1024)).toFixed(2)} MB selected
                  </span>
                </>
              ) : (
                <>
                  <strong>Drop your video here</strong>
                  <span>or click to browse your computer</span>
                </>
              )}

              <small>MP4, MOV, WebM or MKV · Maximum 100 MB</small>
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.mov,.mkv,.webm,video/mp4,video/quicktime,video/webm"
              hidden
              onChange={(event) => selectFile(event.target.files?.[0])}
            />

            <div className="upload-hint">
              ▣{" "}
              {file
                ? "Video selected. Ready to upload and dub."
                : "Select a video to start your dubbing project."}
            </div>
          </div>

          <div className="panel language-panel">
            <div className="panel-heading">
              <span className="icon-box">文</span>

              <div>
                <h3>Language settings</h3>
                <p>Choose your source and target languages.</p>
              </div>
            </div>

            <label htmlFor="source-language">SOURCE LANGUAGE</label>

            <select
              id="source-language"
              value={source}
              onChange={(event) => setSource(event.target.value)}
              disabled={busy}
            >
              {languages.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.name}
                </option>
              ))}
            </select>

            <div className="language-divider">
              <span />
              <span>文</span>
              <span />
            </div>

            <label htmlFor="target-language">TARGET LANGUAGE</label>

            <select
              id="target-language"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              disabled={busy}
            >
              {languages.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.name}
                </option>
              ))}
            </select>

            <div className="language-pair">
              <small>Selected language pair</small>
              <strong>
                {sourceName} → {targetName}
              </strong>
            </div>

            <p className="language-note">
              The backend detects the spoken source language automatically.
            </p>
          </div>
        </section>

        <section className="bottom-panel">
          <div className="panel-heading">
            <span className="icon-box">✧</span>

            <div>
              <h3>
                {status === "success"
                  ? "Your dubbed video is ready!"
                  : status === "uploading"
                    ? "Uploading your video..."
                    : status === "dubbing"
                      ? "Creating your dubbed video..."
                      : "Ready for AI dubbing?"}
              </h3>

              <p>
                {status === "uploading"
                  ? "Sending your video to the backend."
                  : status === "dubbing"
                    ? "Transcribing, translating and generating speech. Please wait."
                    : status === "success"
                      ? "Download and listen to your translated video."
                      : "Select a video to begin the dubbing workflow."}
              </p>
            </div>
          </div>

          <button
            type="button"
            className="primary-button"
            onClick={createDub}
            disabled={!file || busy}
          >
            {busy
              ? "Please wait..."
              : status === "success"
                ? "Create again"
                : "⊙ Create dubbed video"}
          </button>
        </section>

        {busy && (
          <div className="status-message" role="status">
            <span className="spinner" />

            {status === "uploading"
              ? "Uploading video..."
              : "Generating your dubbed video. This may take a little while..."}
          </div>
        )}

        {error && (
          <div className="error-message" role="alert">
            <strong>ⓘ</strong>
            <span>{error}</span>
          </div>
        )}

        {uploadInfo && (
          <section className="panel details-panel">
            <div className="panel-heading">
              <span className="icon-box">✓</span>

              <div>
                <h3>Upload details</h3>
                <p>Your video has been received by the backend.</p>
              </div>
            </div>

            <div className="details-grid">
              <div>
                <small>Filename</small>
                <strong>{uploadInfo.filename || file?.name}</strong>
              </div>

              <div>
                <small>File size</small>
                <strong>
                  {(
                    (uploadInfo.size_bytes || file?.size || 0) /
                    (1024 * 1024)
                  ).toFixed(2)}{" "}
                  MB
                </strong>
              </div>

              <div>
                <small>Target language</small>
                <strong>{targetName}</strong>
              </div>

              <div>
                <small>Upload status</small>
                <strong>Successful</strong>
              </div>
            </div>

            <small className="file-id">File ID: {fileId}</small>
          </section>
        )}

        {result && (
          <section className="panel result-panel">
            <div className="panel-heading">
              <span className="icon-box">✓</span>

              <div>
                <h3>Dubbing completed successfully</h3>

                <p>
                  {result.source_language || sourceName} →{" "}
                  {result.target_language || targetName}
                </p>
              </div>
            </div>

            {result.translated_text && (
              <div className="translation-preview">
                <h4>Translated speech</h4>
                <p>{result.translated_text}</p>
              </div>
            )}

            <div className="result-actions">
              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  downloadFile("/download", `voxdub_${fileId}.mp4`)
                }
              >
                ↓ Download dubbed video
              </button>

              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  downloadFile("/subtitles", `voxdub_${fileId}.srt`)
                }
              >
                ↓ Download subtitles
              </button>
            </div>
          </section>
        )}

        <footer className="footer">
          <strong>VOXDUB AI</strong>
          <span>Multilingual video dubbing platform</span>
        </footer>
      </main>
    </div>
  );
}
