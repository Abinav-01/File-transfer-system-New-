"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { ApiError, downloadFile, getPublicFile, type PublicFile } from "@/lib/api";
import { formatDate, formatSize, remaining } from "@/lib/format";

type ViewState = "loading" | "active" | "expired" | "limited" | "deleted" | "invalid" | "unavailable";
function stateFor(file: PublicFile): ViewState {
  if (file.status === "DELETED") return "deleted";
  if (file.status === "EXPIRED" || new Date(file.expires_at).getTime() <= Date.now()) return "expired";
  if (file.status === "DOWNLOAD_LIMIT_REACHED" || (file.max_downloads !== null && file.download_count >= file.max_downloads)) return "limited";
  return "active";
}
function stateMessage(state: ViewState): string {
  return ({ expired: "This link has expired.", limited: "This file has reached its download limit.", deleted: "This file was deleted by its owner.", invalid: "This link is invalid or no longer exists.", unavailable: "DropVault is temporarily unavailable. Please try again later.", loading: "Loading file…", active: "" })[state];
}
export default function DownloadPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [file, setFile] = useState<PublicFile | null>(null);
  const [state, setState] = useState<ViewState>("loading");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  useEffect(() => {
    let active = true;
    getPublicFile(token).then((value) => { if (active) { setFile(value); setState(stateFor(value)); } }).catch((reason) => { if (active) setState(reason instanceof ApiError && reason.status === 404 ? "invalid" : "unavailable"); });
    return () => { active = false; };
  }, [token]);
  async function start(event: React.FormEvent) {
    event.preventDefault(); if (!file) return;
    setBusy(true); setError(""); setDone(false);
    try {
      const blob = await downloadFile(token, password);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = file.filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setDone(true);
      setFile((current) => current ? { ...current, download_count: current.download_count + 1 } : current);
      if (file.max_downloads !== null && file.download_count + 1 >= file.max_downloads) setState("limited");
    } catch (reason) {
      if (reason instanceof ApiError) {
        if (reason.status === 401) setError("Incorrect password. Please try again.");
        else if (reason.status === 429) setError(reason.message);
        else if (reason.status === 404) setState("invalid");
        else if (reason.status === 410) { setState(reason.message === "File expired" ? "expired" : reason.message === "File deleted" ? "deleted" : "limited"); }
        else setState("unavailable");
      } else setState("unavailable");
    } finally { setBusy(false); }
  }
  return <Shell><div className="page-width narrow-page">
    <div className="page-heading center"><div className="eyebrow">SECURE DOWNLOAD</div><h1>{state === "loading" ? "Checking your link" : state === "active" ? "A file is ready for you" : "Link unavailable"}</h1><p>{state === "active" ? "Review the details before downloading." : stateMessage(state)}</p></div>
    {done && <p className="success-message" role="status">Your download has started.</p>}
    {state === "loading" ? <div className="card centered-card" role="status">Loading file details…</div> : state !== "active" ? <div className="card centered-card"><div className="unavailable-icon">!</div><h2>{stateMessage(state)}</h2><Link className="text-link" href="/">Create your own secure link →</Link></div> : file && <div className="card detail-card"><div className="file-summary"><div className="file-glyph">▤</div><div><strong>{file.filename}</strong><span>{formatSize(file.size_bytes)}</span></div></div><div className="detail-grid"><div><span>Expires</span><strong>{formatDate(file.expires_at)}</strong><small>{remaining(file.expires_at)}</small></div><div><span>Downloads remaining</span><strong>{file.max_downloads === null ? "Unlimited" : Math.max(0, file.max_downloads - file.download_count)}</strong></div></div>
      <form onSubmit={start}>{file.password_required && <div className="field download-password"><label htmlFor="download-password">Password required</label><input id="download-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter the file password" required /></div>}{error && <p className="error-message" role="alert">{error}</p>}<button className="button button-primary full-width" disabled={busy} type="submit">{busy ? "Preparing download…" : "Download File"}<span aria-hidden="true">↓</span></button></form>
    </div>}
  </div></Shell>;
}
