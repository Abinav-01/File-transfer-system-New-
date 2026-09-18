export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const unit = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** unit).toFixed(bytes / 1024 ** unit < 10 ? 1 : 0)} ${["B", "KB", "MB", "GB", "TB"][unit]}`;
}
export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
export function remaining(value: string): string {
  const ms = new Date(value).getTime() - Date.now();
  if (ms <= 0) return "Expired";
  const hours = Math.ceil(ms / 3_600_000);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} left`;
  const days = Math.ceil(ms / 86_400_000);
  return `${days} day${days === 1 ? "" : "s"} left`;
}
export function downloadLimit(value: number | null): string { return value === null ? "Unlimited" : String(value); }
