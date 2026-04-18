"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { deleteFile, getManagedFile, type ManagedFile } from "@/lib/api";
import { listLocalUploads, removeLocalUpload, shareUrl, type LocalUpload } from "@/lib/local-files";
import { formatDate, formatSize } from "@/lib/format";

type Entry = { local: LocalUpload; remote?: ManagedFile; error?: string };
function displayStatus(entry: Entry): string {
  if (entry.remote?.status === "DELETED") return "Deleted";
  if (entry.remote?.status === "DOWNLOAD_LIMIT_REACHED") return "Limit reached";
  if (entry.remote?.status === "EXPIRED" || new Date(entry.local.expires_at).getTime() <= Date.now()) return "Expired";
  return entry.remote ? "Active" : "Unknown";
}
export default function DashboardPage() {
  const [entries, setEntries] = useState<Entry[] | null>(null);
  const [busyId, setBusyId] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    const local = listLocalUploads();
    Promise.all(local.map(async (item): Promise<Entry> => {
      try { return { local: item, remote: await getManagedFile(item.id, item.management_token) }; }
      catch { return { local: item, error: "Status unavailable" }; }
    })).then(setEntries);
  }, []);
  async function copy(token: string) {
    try { await navigator.clipboard.writeText(shareUrl(token)); setMessage("Link copied."); }
    catch { setMessage("Could not copy the link. Open it and copy from the address bar."); }
  }
  async function remove(entry: Entry) {
    if (!window.confirm(`Delete ${entry.local.original_filename}? Its share link will stop working.`)) return;
    setBusyId(entry.local.id); setMessage("");
    try { await deleteFile(entry.local.id, entry.local.management_token); removeLocalUpload(entry.local.id); setEntries((current) => current?.filter((item) => item.local.id !== entry.local.id) || []); setMessage("File deleted."); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : "Could not delete the file."); }
    finally { setBusyId(""); }
  }
  return <Shell><div className="page-width dashboard-page"><div className="dashboard-heading"><div><div className="eyebrow">THIS BROWSER</div><h1>My files</h1><p>Files you created here are remembered on this device.</p></div><Link href="/" className="button button-primary">+ New upload</Link></div>
    {message && <p className="info-message" role="status">{message}</p>}
    {entries === null ? <div className="card centered-card" role="status">Loading your files…</div> : entries.length === 0 ? <div className="card centered-card"><div className="empty-icon">▤</div><h2>No files yet</h2><p>Upload a file to see it here.</p><Link href="/" className="button button-primary">Upload a file</Link></div> : <div className="file-list">{entries.map((entry) => <article className="card dashboard-row" key={entry.local.id}><div className="dashboard-file"><div className="file-glyph">▤</div><div><strong>{entry.local.original_filename}</strong><small>{formatSize(entry.local.size_bytes)}</small></div></div><div className="dashboard-meta"><div><span>Created</span><strong>{formatDate(entry.remote?.created_at || entry.local.created_at)}</strong></div><div><span>Expires</span><strong>{formatDate(entry.local.expires_at)}</strong></div><div><span>Downloads</span><strong>{entry.remote ? `${entry.remote.download_count}${entry.remote.max_downloads === null ? "" : ` / ${entry.remote.max_downloads}`}` : "—"}</strong></div><div><span>Status</span><strong className={`status-pill ${displayStatus(entry).toLowerCase().replaceAll(" ", "-")}`}>{displayStatus(entry)}</strong></div></div><div className="dashboard-actions"><Link href={`/d/${encodeURIComponent(entry.local.share_token)}`} className="text-link">Open link</Link><button className="text-button" onClick={() => copy(entry.local.share_token)}>Copy link</button><button className="text-button danger" disabled={busyId === entry.local.id} onClick={() => remove(entry)}>{busyId === entry.local.id ? "Deleting…" : "Delete"}</button></div>{entry.error && <small className="muted">{entry.error}</small>}</article>)}</div>}
    <p className="dashboard-note">Management details are stored only in this browser. Clearing browser storage removes access to these controls.</p>
  </div></Shell>;
}
