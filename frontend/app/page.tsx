
"use client";

import { useRef, useState } from "react";

type Operation = "to_mp3" | "to_mp4" | "compress";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [operation, setOperation] = useState<Operation>("to_mp3");
  const [bitrate, setBitrate] = useState("192k");
  const [quality, setQuality] = useState("balanced");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function processFile() {
    if (!file) return;

    setBusy(true);
    setError("");
    setSuccess("");

    const body = new FormData();
    body.append("file", file);
    body.append("operation", operation);
    body.append("audio_bitrate", bitrate);
    body.append("quality", quality);

    try {
      const response = await fetch(`${API_BASE}/api/process`, {
        method: "POST",
        body,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Processing failed.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");

      a.href = url;
      a.download =
        operation === "to_mp3"
          ? "your-media-tools-audio.mp3"
          : operation === "compress"
            ? "your-media-tools-compressed.mp4"
            : "your-media-tools-video.mp4";

      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setSuccess("Your download has started!");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const tools = [
    {
      id: "to_mp3" as const,
      title: "Video to MP3",
      desc: "Extract audio from videos",
      icon: "♫",
    },
    {
      id: "to_mp4" as const,
      title: "Convert to MP4",
      desc: "Convert supported video formats",
      icon: "▶",
    },
    {
      id: "compress" as const,
      title: "Compress Video",
      desc: "Reduce video file size",
      icon: "⇩",
    },
  ];

  return (
    <main>
      <nav className="nav wrap">
        <a className="brand" href="#">
          <span className="brand-mark">M</span>
          <span>Your Media <b>Tools</b></span>
        </a>
        <a className="nav-link" href="#tools">Media Tools</a>
      </nav>

      <section className="hero wrap">
        <div className="eyebrow">
          <span className="pulse" />
          SIMPLE · FAST · ONLINE
        </div>

        <h1>
          Your media.
          <br />
          <span>Made more useful.</span>
        </h1>

        <p className="hero-copy">
          Convert audio, transform videos and reduce file sizes
          with simple online tools.
        </p>

        <div className="workspace">
          <div className="workspace-head">
            <b>01 · Choose your media</b>
            <span className="muted">
              MP4 · MOV · MKV · MP3 · WAV
            </span>
          </div>

          <button
            className={`dropzone ${file ? "has-file" : ""}`}
            onClick={() => inputRef.current?.click()}
            type="button"
          >
            <input
              ref={inputRef}
              type="file"
              accept="video/*,audio/*,.mkv,.avi,.flac,.ogg"
              hidden
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setError("");
                setSuccess("");
              }}
            />

            <span className="upload-icon">↑</span>

            <strong>
              {file ? file.name : "Drop a file here or browse"}
            </strong>

            <small>
              {file
                ? `${(file.size / 1048576).toFixed(2)} MB`
                : "Select a video or audio file"}
            </small>
          </button>

          <div className="workspace-head tool-head" id="tools">
            <b>02 · Select a tool</b>
          </div>

          <div className="tool-grid">
            {tools.map((tool) => (
              <button
                type="button"
                key={tool.id}
                className={`tool-card ${
                  operation === tool.id ? "selected" : ""
                }`}
                onClick={() => {
                  setOperation(tool.id);
                  setError("");
                  setSuccess("");
                }}
              >
                <span className="tool-icon">{tool.icon}</span>
                <strong>{tool.title}</strong>
                <small>{tool.desc}</small>
                <span className="radio-dot">
                  {operation === tool.id ? "✓" : ""}
                </span>
              </button>
            ))}
          </div>

          {operation === "to_mp3" && (
            <div className="settings">
              <label htmlFor="bitrate">Audio quality</label>
              <select
                id="bitrate"
                value={bitrate}
                onChange={(e) => setBitrate(e.target.value)}
              >
                <option value="128k">128 kbps</option>
                <option value="192k">192 kbps</option>
                <option value="320k">320 kbps</option>
              </select>
            </div>
          )}

          {operation === "compress" && (
            <div className="settings">
              <label htmlFor="quality">Compression quality</label>
              <select
                id="quality"
                value={quality}
                onChange={(e) => setQuality(e.target.value)}
              >
                <option value="high">High quality</option>
                <option value="balanced">Balanced</option>
                <option value="small">Smaller file</option>
              </select>
            </div>
          )}

          <button
            className="primary"
            onClick={processFile}
            disabled={!file || busy}
          >
            {busy ? "Processing..." : "Process and Download →"}
          </button>

          {error && <p className="message error">{error}</p>}
          {success && <p className="message success">{success}</p>}

          <p className="privacy">
            Process only media you own or are authorized to use.
          </p>
        </div>
      </section>

      <section className="features wrap">
        <div>
          <span>01 / CONVERT</span>
          <h3>Audio and Video</h3>
          <p>Convert supported files to MP3 and MP4.</p>
        </div>

        <div>
          <span>02 / COMPRESS</span>
          <h3>Reduce File Size</h3>
          <p>Compress videos with adjustable quality.</p>
        </div>

        <div>
          <span>03 / SIMPLE</span>
          <h3>Easy to Use</h3>
          <p>Designed for desktop and mobile devices.</p>
        </div>
      </section>

      <footer className="wrap footer">
        <span>© {new Date().getFullYear()} Your Media Tools</span>
        <span>All rights reserved.</span>
      </footer>
    </main>
  );
}
