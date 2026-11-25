import { tokenStore } from "./api";

/** 受保护的文件接口需要 Bearer，直接 window.open 会 401；这里取 blob 再触发下载。 */
export async function downloadWithAuth(url: string, filename: string): Promise<void> {
  const token = tokenStore.get();
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename || "resume";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
