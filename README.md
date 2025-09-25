# Artos ICF RAG — Take‑Home Project

This repository contains a full end‑to‑end RAG pipeline and a Vite + React UI for generating Informed Consent Form (ICF) sections from a protocol PDF, refining them with a second pass, and exporting a DOCX. It is structured as a simple Flask backend (ArtosBackend) plus a Vite app (ArtosViteJS).

## What’s Inside
- Backend (Flask): upload, ingest, retrieval, generate, generate+refine, runs (logs + docx), and docs (OpenAPI + Swagger UI).
- Services: vectorization (FAISS + BM25), retrieval, LLM chains, refinement, DOCX assembly.
- Frontend (Vite + React): single‑page flow for upload → ingest → generate+refine → preview → download DOCX/logs.

## Prerequisites
- Python 3.9+ (3.10+ recommended)
- Node.js 18+ and npm
- Google Generative AI key (GOOGLE_API_KEY) for embeddings/LLM
- Pandoc installed (for DOCX export) and the `pypandoc` Python package
  - macOS: `brew install pandoc`
  - Ubuntu/Debian: `sudo apt-get install pandoc`

## Getting Started

### 1) Clone the repo
```bash
git clone <your-fork-or-https-url>
cd ArtosTakehome
```

### 2) Backend — setup and run
```bash
cd ArtosBackend

# Create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pypandoc  # required for DOCX assembly

# Set your Google API Key (required for embeddings/LLM)
export GOOGLE_API_KEY=your_key_here
# or create an .env file in ArtosBackend with:
# GOOGLE_API_KEY=your_key_here

# Run the API (default: http://127.0.0.1:5000)
python3 -m app.main
```

Useful endpoints:
- Health: `GET /health`
- OpenAPI: `GET /openapi.yaml`
- Swagger UI: `GET /docs`

Data is written under `ArtosBackend/data/` (files, indexes, runs, db).

### 3) Frontend — setup and run
```bash
cd ../ArtosViteJS
npm install
npm run dev
```

Open the Vite dev server (usually http://localhost:5173). The app proxies `/api` to `http://127.0.0.1:5000` by default (see `vite.config.js`).

## Basic Flow (UI)
1) Upload a PDF (or DOCX).
2) Click “Generate ICF Sections” — this runs generate + refine in one shot.
3) Preview per‑section text.
4) Download DOCX or Logs.

## Basic Flow (API)
- Upload:
  ```bash
  curl -sS -X POST http://127.0.0.1:5000/upload \
       -F file=@your.pdf | jq
  # → { "file_id": "FILE_..." }
  ```
- Ingest:
  ```bash
  curl -sS -X POST http://127.0.0.1:5000/ingest \
       -H 'Content-Type: application/json' \
       -d '{"file_id":"FILE_..."}' | jq
  ```
- Generate + Refine in one call:
  ```bash
  curl -sS -X POST http://127.0.0.1:5000/refine \
       -H 'Content-Type: application/json' \
       -d '{"file_id":"FILE_..."}' | jq
  # → { "run_id": "RUN_...", "status": "refined", "sections": { ... }, "queries": { ... } }
  ```
- Download DOCX:
  ```bash
  curl -L -o ICF_RUN_XXXX.docx http://127.0.0.1:5000/runs/RUN_XXXX/docx
  ```
- Download Logs:
  ```bash
  curl -sS http://127.0.0.1:5000/runs/RUN_XXXX/logs | jq
  ```

## Notes & Tips
- If DOCX download fails, ensure Pandoc is installed and `pypandoc` is in your virtualenv.
- You can set a custom data directory via `ARTOS_DATA_DIR` if desired.
- The Vite dev server proxies `/api` by default; to call the backend directly from the browser (no proxy), set `VITE_API_BASE` in an `.env` or shell to `http://127.0.0.1:5000`.
- For retrieval debugging, use `POST /search` with an `index_id` and a query to inspect hits.

Enjoy exploring the pipeline!

