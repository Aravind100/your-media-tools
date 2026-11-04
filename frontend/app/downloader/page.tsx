
"use client";

import { useState } from "react";
import {
  detectPlatform,
  PlatformResult,
} from "../../lib/platforms";

export default function DownloaderPage() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<PlatformResult | null>(null);

  function handleCheck() {
    if (!url.trim()) {
      setResult({
        platform: "unknown",
        valid: false,
        message: "Please paste a video URL first.",
      });
      return;
    }

    setResult(detectPlatform(url));
  }

  const isYouTube = result?.platform === "youtube" && result.valid;

  return (
    <main style={styles.page}>
      <div style={styles.container}>
        <a href="/" style={styles.back}>← Back to Home</a>

        <div style={styles.hero}>
          <div style={styles.icon}>▶</div>
          <h1 style={styles.heading}>Social Media Downloader</h1>
          <p style={styles.subtitle}>
            Check media links and access supported, authorized content.
          </p>
        </div>

        <section style={styles.card}>
          <label style={styles.label}>Paste your video URL</label>

          <div style={styles.inputRow}>
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setResult(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCheck();
              }}
              placeholder="https://www.youtube.com/watch?v=..."
              style={styles.input}
            />

            <button onClick={handleCheck} style={styles.button}>
              Check URL
            </button>
          </div>

          <p style={styles.hint}>
            Supported platforms: YouTube, Instagram, Facebook and X.
          </p>

          {result && (
            <div
              style={{
                ...styles.result,
                borderColor: result.valid ? "#16a34a" : "#dc2626",
              }}
            >
              <strong>
                {result.valid ? "✓ Link recognized" : "Link not recognized"}
              </strong>
              <p style={{ marginBottom: 0 }}>{result.message}</p>
            </div>
          )}

          {isYouTube && result.videoId && (
            <div style={styles.videoSection}>
              <h2 style={styles.subheading}>YouTube video preview</h2>

              <div style={styles.videoFrame}>
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${result.videoId}`}
                  title="YouTube video preview"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                  style={styles.iframe}
                />
              </div>

              <a
                href={result.normalizedUrl}
                target="_blank"
                rel="noreferrer"
                style={styles.youtubeLink}
              >
                Open video on YouTube ↗
              </a>

              <div style={styles.notice}>
                <strong>Authorized content only</strong>
                <p>
                  YouTube video and audio extraction is not available through
                  this tool without the required platform authorization.
                  If you own the original video file or have permission to use
                  it, upload that file to our existing conversion tools.
                </p>
              </div>
            </div>
          )}
        </section>

        <section style={styles.platforms}>
          <h2 style={styles.subheading}>Supported platforms</h2>
          <div style={styles.platformGrid}>
            {["YouTube", "Instagram", "Facebook", "X / Twitter"].map(
              (platform) => (
                <div key={platform} style={styles.platform}>
                  {platform}
                </div>
              )
            )}
          </div>
          <p style={styles.footer}>
            Features depend on each platform's official API and content
            permissions.
          </p>
        </section>
      </div>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "#f3f6fb",
    padding: "35px 16px",
    color: "#172033",
  },
  container: {
    maxWidth: "850px",
    margin: "0 auto",
  },
  back: {
    color: "#2457c5",
    textDecoration: "none",
    fontWeight: 600,
  },
  hero: {
    textAlign: "center",
    padding: "35px 10px 25px",
  },
  icon: {
    width: 58,
    height: 58,
    margin: "0 auto 16px",
    borderRadius: 18,
    background: "#2457c5",
    color: "white",
    display: "grid",
    placeItems: "center",
    fontSize: 27,
  },
  heading: {
    fontSize: "clamp(27px, 5vw, 38px)",
    margin: "0 0 10px",
  },
  subtitle: {
    color: "#64748b",
    margin: 0,
  },
  card: {
    background: "white",
    padding: "26px",
    borderRadius: 18,
    boxShadow: "0 8px 30px rgba(20,40,80,0.07)",
  },
  label: {
    display: "block",
    fontWeight: 700,
    marginBottom: 12,
  },
  inputRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  input: {
    flex: "1 1 300px",
    minWidth: 0,
    padding: "15px",
    border: "1px solid #d5dce8",
    borderRadius: 10,
    fontSize: 15,
  },
  button: {
    background: "#2457c5",
    color: "white",
    border: 0,
    borderRadius: 10,
    padding: "14px 24px",
    fontWeight: 700,
    cursor: "pointer",
  },
  hint: {
    fontSize: 13,
    color: "#64748b",
    marginTop: 12,
  },
  result: {
    marginTop: 22,
    padding: 16,
    border: "1px solid",
    borderRadius: 10,
    background: "#f8fafc",
  },
  videoSection: {
    marginTop: 25,
  },
  subheading: {
    fontSize: 20,
    marginBottom: 15,
  },
  videoFrame: {
    position: "relative",
    width: "100%",
    aspectRatio: "16 / 9",
    overflow: "hidden",
    borderRadius: 12,
    background: "#111827",
  },
  iframe: {
    width: "100%",
    height: "100%",
    border: 0,
    position: "absolute",
    inset: 0,
  },
  youtubeLink: {
    display: "inline-block",
    marginTop: 14,
    color: "#2457c5",
    fontWeight: 700,
    textDecoration: "none",
  },
  notice: {
    marginTop: 20,
    padding: 16,
    borderRadius: 10,
    background: "#eff6ff",
    color: "#1e40af",
    lineHeight: 1.6,
    fontSize: 14,
  },
  platforms: {
    marginTop: 30,
    background: "white",
    borderRadius: 18,
    padding: 24,
  },
  platformGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
    gap: 12,
  },
  platform: {
    padding: 16,
    textAlign: "center",
    background: "#f3f6fb",
    borderRadius: 10,
    fontWeight: 700,
  },
  footer: {
    color: "#64748b",
    fontSize: 13,
    marginBottom: 0,
    marginTop: 16,
  },
};
