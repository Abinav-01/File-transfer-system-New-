"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { deleteFile } from "@/lib/api";
import { getLocalUpload, removeLocalUpload, shareUrl, type LocalUpload } from "@/lib/local-files";
import { downloadLimit, formatDate, formatSize } from "@/lib/format";

export default function SuccessPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [upload, setUpload] = useState<LocalUpload | null | undefined>(undefined);
  const [copied, setCopied] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { queueMicrotask(() => setUpload(getLocalUpload(id) || null)); }, [id]);
  async function copy() {
    if (!upload) return;
    try { await navigator.clipboard.writeText(shareUrl(upload.share_token)); setCopied(true); setTimeout(() => setCopied(false), 2500); }
    catch { setError("Could not copy automatically. Select and copy the link instead."); }
  }
  async function remove() {
    if (!upload || !window.confirm("Delete this file now? Its share link will stop working.")) return;
    setDeleting(true); setError("");
    try { await deleteFile(upload.id, upload.management_token); removeLocalUpload(upload.id); setDeleted(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not delete the file."); }
    finally { setDeleting(false); }
  }
  return <Shell><div className="page-width narrow-page">
    {upload === undefined ? <div className="card centered-card">Loading…</div> : deleted ? <div className="card centered-card"><div className="result-icon">✓</div><h1>File deleted</h1><p>The share link can no longer be used.</p><Link className="button button-primary" href="/dashboard">Go to my files</Link></div> : !upload ? <div className="card centered-card"><h1>Upload details unavailable</h1><p>This browser does not have management details for this upload.</p><Link className="button button-primary" href="/">Upload a file</Link></div> : <>
      <div className="page-heading center"><div className="result-icon">✓</div><div className="eyebrow">UPLOAD COMPLETE</div><h1>Your secure link is ready</h1><p>Share the link with anyone who should have access to this file.</p></div>
      <div className="card detail-card"><div className="file-summary"><div className="file-glyph">▤</div><div><strong>{upload.original_filename}</strong><span>{formatSize(upload.size_bytes)}</span></div></div><div className="detail-grid"><div><span>Expires</span><strong>{formatDate(upload.expires_at)}</strong></div><div><span>Download limit</span><strong>{downloadLimit(upload.max_downloads)}</strong></div></div>
        <div className="share-section"><label htmlFor="share-link">Share link</label><div className="share-row"><input id="share-link" readOnly value={shareUrl(upload.share_token)} onFocus={(event) => event.target.select()} /><button className="button button-primary" type="button" onClick={copy}>{copied ? "Copied" : "Copy Link"}</button></div><small>Keep your management controls in this browser. The share link contains no management token.</small></div>
        {error && <p className="error-message" role="alert">{error}</p>}
      </div>
      <div className="action-row"><Link href="/dashboard" className="text-link">View my files →</Link><button className="text-button danger" type="button" onClick={remove} disabled={deleting}>{deleting ? "Deleting…" : "Delete File"}</button></div>
    </>}
  </div></Shell>;
}
