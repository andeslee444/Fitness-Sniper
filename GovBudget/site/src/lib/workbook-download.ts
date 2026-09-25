/** Fetch the unchanged saved government bytes, verify them, then name the download. */
export async function downloadWorkbook(url: string, filename: string, sha256: string): Promise<void> {
  if (!/^[a-f0-9]{64}$/i.test(sha256)) throw new Error("Workbook identity is missing");
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Workbook download failed (${response.status})`);
  const bytes = await response.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const actual = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  if (actual !== sha256.toLowerCase()) throw new Error("Workbook did not match the recorded source");
  const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.hidden = true;
  document.body.appendChild(anchor);
  try { anchor.click(); }
  finally {
    anchor.remove();
    // Keep the URL alive while the browser starts saving the file.
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  }
}
