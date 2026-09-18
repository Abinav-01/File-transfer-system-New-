import type { CreatedUpload } from "./api";

export type LocalUpload = CreatedUpload & { created_at: string };
const KEY = "dropvault:uploads:v1";

export function listLocalUploads(): LocalUpload[] {
  if (typeof window === "undefined") return [];
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(value) ? value.filter((item) => item && typeof item.id === "string" && typeof item.management_token === "string") : [];
  } catch { return []; }
}
export function getLocalUpload(id: string): LocalUpload | undefined {
  return listLocalUploads().find((item) => item.id === id);
}
export function saveLocalUpload(upload: CreatedUpload): void {
  const next = [{ ...upload, created_at: new Date().toISOString() }, ...listLocalUploads().filter((item) => item.id !== upload.id)];
  localStorage.setItem(KEY, JSON.stringify(next));
}
export function removeLocalUpload(id: string): void {
  localStorage.setItem(KEY, JSON.stringify(listLocalUploads().filter((item) => item.id !== id)));
}
export function shareUrl(token: string): string {
  return `${window.location.origin}/d/${encodeURIComponent(token)}`;
}
