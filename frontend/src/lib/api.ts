export type UploadStatus = "ACTIVE" | "EXPIRED" | "DOWNLOAD_LIMIT_REACHED" | "DELETED";
export type CreatedUpload = {
  id: string;
  original_filename: string;
  size_bytes: number;
  expires_at: string;
  max_downloads: number | null;
  share_token: string;
  management_token: string;
};
export type PublicFile = {
  filename: string;
  size_bytes: number;
  expires_at: string;
  password_required: boolean;
  status: UploadStatus;
  max_downloads: number | null;
  download_count: number;
};
export type ManagedFile = {
  id: string;
  original_filename: string;
  size_bytes: number;
  expires_at: string;
  max_downloads: number | null;
  download_count: number;
  status: UploadStatus;
  share_token: string;
  created_at: string;
};

const BASE = "/backend";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}

function errorMessage(status: number, detail?: string): string {
  if (status === 429) return detail || "Too many attempts. Please try again later.";
  if (status >= 500) return "The service is temporarily unavailable. Please try again.";
  return detail || "The request could not be completed.";
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") detail = body.detail;
  } catch { /* A proxy or network error may return HTML. */ }
  return new ApiError(response.status, errorMessage(response.status, detail));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(BASE + path, { cache: "no-store", ...init }); }
  catch { throw new ApiError(0, "Cannot reach DropVault. Check your connection and try again."); }
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

export function uploadFile(
  file: File,
  options: { expiresIn: number; maxDownloads: number | null; password: string | null },
  onProgress: (percent: number) => void,
): Promise<CreatedUpload> {
  const data = new FormData();
  data.append("file", file);
  data.append("expires_in", String(options.expiresIn));
  if (options.maxDownloads !== null) data.append("max_downloads", String(options.maxDownloads));
  if (options.password) data.append("password", options.password);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", BASE + "/api/uploads");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new ApiError(0, "Cannot reach DropVault. Check your connection and try again."));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText) as CreatedUpload); }
        catch { reject(new ApiError(0, "The server returned an unexpected response.")); }
        return;
      }
      let detail: string | undefined;
      try { detail = JSON.parse(xhr.responseText).detail; } catch { /* ignore */ }
      reject(new ApiError(xhr.status, errorMessage(xhr.status, detail)));
    };
    xhr.send(data);
  });
}

export const getPublicFile = (token: string) => request<PublicFile>(`/api/uploads/${encodeURIComponent(token)}`);
export const getManagedFile = (id: string, managementToken: string) =>
  request<ManagedFile>(`/api/uploads/manage/${encodeURIComponent(id)}`, { headers: { "X-Management-Token": managementToken } });
export async function deleteFile(id: string, managementToken: string): Promise<void> {
  let response: Response;
  try { response = await fetch(BASE + `/api/uploads/${encodeURIComponent(id)}`, { method: "DELETE", headers: { "X-Management-Token": managementToken } }); }
  catch { throw new ApiError(0, "Cannot reach DropVault. Check your connection and try again."); }
  if (!response.ok) throw await parseError(response);
}
export async function downloadFile(token: string, password?: string): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(BASE + `/api/files/${encodeURIComponent(token)}/download`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: password || null }),
    });
  } catch { throw new ApiError(0, "Cannot reach DropVault. Check your connection and try again."); }
  if (!response.ok) throw await parseError(response);
  return response.blob();
}
