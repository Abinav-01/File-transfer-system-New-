"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/shell";
import { uploadFile } from "@/lib/api";
import { saveLocalUpload } from "@/lib/local-files";
import { formatSize } from "@/lib/format";

const expirations = [{ label: "1 hour", value: 60 }, { label: "6 hours", value: 360 }, { label: "24 hours", value: 1440 }, { label: "3 days", value: 4320 }, { label: "7 days", value: 10080 }];

export default function Home() {
  const router = useRouter();
  const picker = useRef<HTMLInputElement>(null);
  useEffect(() => { picker.current?.setAttribute("data-ready", "true"); }, []);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [expiresIn, setExpiresIn] = useState(1440);
  const [limitChoice, setLimitChoice] = useState("unlimited");
  const [customLimit, setCustomLimit] = useState(2);
  const [protect, setProtect] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  function choose(next?: File) {
    if (!next) return;
    setFile(next);
    setError("");
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) { setError("Select a file to continue."); return; }
    if (file.size === 0) { setError("Choose a file that is not empty."); return; }
    if (protect && !password.trim()) { setError("Enter a password or turn off password protection."); return; }
    if (limitChoice === "custom" && (!Number.isInteger(customLimit) || customLimit < 1)) { setError("Enter a positive whole number for the download limit."); return; }
    setBusy(true); setProgress(0); setError("");
    try {
      const created = await uploadFile(file, {
        expiresIn,
        maxDownloads: limitChoice === "unlimited" ? null : limitChoice === "custom" ? customLimit : Number(limitChoice),
        password: protect ? password : null,
      }, setProgress);
      try { saveLocalUpload(created); }
      catch { setError("The file uploaded, but this browser could not save its management details. Enable browser storage and try again."); setBusy(false); return; }
      router.push(`/success/${created.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed. Please try again.");
      setBusy(false);
    }
  }

  return <Shell><div className="page-width upload-layout">
    <section className="intro-panel"><div className="eyebrow">SECURE FILE SHARING</div><h1>Share files temporarily and securely.</h1><p>Send what matters without leaving it online forever. Choose how long your link lasts and who can access it.</p><div className="trust-line"><span className="trust-icon">✓</span> Your files expire automatically</div></section>
    <section className="card upload-card" aria-labelledby="upload-title"><div className="card-top"><span className="step-label">01 / NEW SHARE</span><h2 id="upload-title">Create a secure link</h2><p>Set a few controls, then share with confidence.</p></div>
      <form onSubmit={submit}>
        <input ref={picker} type="file" data-testid="upload-file-input" className="sr-only" aria-label="Select file" onChange={(event) => choose(event.target.files?.[0])} />
        <div className={`dropzone ${dragging ? "dragging" : ""}`} role="button" tabIndex={0} aria-label="Choose file or drop it here" onClick={() => picker.current?.click()} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); picker.current?.click(); } }} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }}>
          <span className="upload-icon" aria-hidden="true">↑</span>
          {file ? <><strong className="file-name">{file.name}</strong><span className="muted">{formatSize(file.size)} · Click to choose a different file</span></> : <><strong>Drag and drop your file here</strong><span className="muted">or choose a file from your device</span></>}
          <span className="button button-secondary select-button">Select File</span>
        </div>
        <div className="form-grid"><div className="field"><label htmlFor="expiration">Expiration</label><select id="expiration" value={expiresIn} onChange={(event) => setExpiresIn(Number(event.target.value))}>{expirations.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
          <div className="field"><label htmlFor="download-limit">Maximum downloads</label><select id="download-limit" value={limitChoice} onChange={(event) => setLimitChoice(event.target.value)}><option value="unlimited">Unlimited</option><option value="1">1 download</option><option value="5">5 downloads</option><option value="10">10 downloads</option><option value="custom">Custom</option></select></div></div>
        {limitChoice === "custom" && <div className="field custom-field"><label htmlFor="custom-limit">Custom download limit</label><input id="custom-limit" type="number" min="1" step="1" value={customLimit} onChange={(event) => setCustomLimit(Number(event.target.value))} /></div>}
        <div className="password-block"><label className="check-row"><input type="checkbox" checked={protect} onChange={(event) => setProtect(event.target.checked)} /><span><strong>Password protection</strong><small>Only people with your password can download.</small></span></label>{protect && <div className="field password-field"><label htmlFor="upload-password">Password</label><input id="upload-password" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter a password" /></div>}</div>
        {error && <p className="error-message" role="alert">{error}</p>}
        {busy && <div className="progress-wrap" aria-live="polite"><span>Uploading… {progress}%</span><progress max="100" value={progress} /></div>}
        <button className="button button-primary full-width" type="submit" disabled={busy}>{busy ? "Creating secure link…" : "Create Secure Link"}<span aria-hidden="true">↗</span></button>
      </form>
    </section>
  </div></Shell>;
}
