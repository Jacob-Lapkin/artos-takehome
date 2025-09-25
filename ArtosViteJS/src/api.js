// Use dev proxy by default to avoid CORS in local dev
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function uploadFile(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function ingest(file_id) {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id }),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function generate(file_id, sections) {
  const body = { file_id };
  if (sections && sections.length) body.sections = sections;
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function generateRefine(file_id, sections, options) {
  const body = { file_id };
  if (sections && sections.length) body.sections = sections;
  if (options && typeof options === 'object') body.options = options;
  const res = await fetch(`${API_BASE}/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function downloadDocx(run_id) {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(run_id)}/docx`);
  if (!res.ok) throw await toApiError(res);
  const blob = await res.blob();
  return blob;
}

export async function getRunLogs(run_id) {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(run_id)}/logs`);
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

async function toApiError(res) {
  let payload;
  try { payload = await res.json(); } catch { /* noop */ }
  const message = payload?.error || `${res.status} ${res.statusText}`;
  const err = new Error(message);
  err.status = res.status;
  err.payload = payload;
  return err;
}

export const api = { uploadFile, ingest, generate, generateRefine, downloadDocx, getRunLogs };
