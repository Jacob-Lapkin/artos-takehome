# Artos Backend — ICF Generation API (Flask) Implementation Plan

This document is your single source of truth to resume and complete the API, even if you’ve forgotten all context. It captures decisions, architecture, endpoints, prompts, retrieval strategy, and a step-by-step execution plan. Preference: use LangChain where practical.

## TL;DR (What to build next)
- Scaffold Flask API with endpoints: `/upload`, `/ingest`, `/generate`, `/runs/{id}`, `/runs/{id}/docx`, `/runs/{id}/logs`, `/search`.
- Implement ingest: parse PDF/DOCX, segment sections, chunk, LLM role-tag, embed, hybrid index (Chroma + in-process BM25) via LangChain.
- Implement per-section generation: hybrid retrieve → (Procedures) extract facts → write → self-check → optional gap-close. Enforce citations inline and in logs.
- Assemble DOCX using a template with placeholders; include inline citations in text (and optionally footnotes).
- Persist artifacts as JSON files; expose logs for grading.

## Goals & Scope
- Input: clinical trial protocol (.pdf or .docx).
- Output: ICF sections (Purpose, Procedures, Risks, Benefits) grounded in the protocol with citations and downloadable DOCX.
- Non-goals: Full ICF, OCR of scanned PDFs (optional later), external DB infra.

## High-Level Lifecycle
Upload → Ingest/Index → Generate (per section) → Self-Check → Gap-Close (optional) → Assemble DOCX → Deliver + Logs → Persist metrics & artifacts

## API Surface (Contracts)
- POST `/upload`
  - In: multipart file (`.pdf|.docx`).
  - Out: `{ file_id, filename, mime, size }`.
  - Do: Persist file under `data/files/{file_id}/source.ext`; store metadata.

- POST `/ingest`
  - In: `{ file_id, store?: "chroma"|"faiss" }`.
  - Out: `{ index_id, n_chunks, store, pages, created_at }`.
  - Do: Parse → segment → chunk → (LLM role-tag) → embed → upsert to vector store + build BM25 → persist index meta.
  - Idempotent by `(file_id, embed_model@version)`.

- POST `/generate`
  - In: `{ file_id, sections?: ["Purpose","Procedures","Risks","Benefits"], options?: { gap_loop_max?: 2, sync?: boolean } }`.
  - Out: `{ run_id, status }` (if async) or `{ run_id, status, sections }` (if sync=true for demo).
  - Do: For each section run retrieval → (extract facts) → write → self-check → (optional gap-close) → persist.

- GET `/runs/{run_id}`
  - Out: `{ status, sections: { Purpose?, Procedures?, Risks?, Benefits? } }` with text, tokens_used, cost, warnings.

- GET `/runs/{run_id}/docx`
  - Out: `ICF_<basename>.docx` stream.

- GET `/runs/{run_id}/logs`
  - Out: provenance JSON including retrieval sets, snippets, citations, facts, sentence map, timings, tokens, costs.

- POST `/search` (debug)
  - In: `{ index_id, query, section?: "Purpose"|"Procedures"|"Risks"|"Benefits", k?: number, filters?: { heading_norm?: string[], role_tag?: string[] }, fuse_weights?: { sparse?: number, dense?: number } }`.
  - Out: `{ hits: [{ chunk_id, page, section_path, heading_norm, preview, score }] }`.

## Storage & State (JSON-backed for MVP)
- Root: `data/`
  - `files/{file_id}/source.ext`
  - `indexes/{index_id}/` (Chroma persist dir or FAISS snapshot + `bm25.json`)
  - `runs/{run_id}/` containing:
    - `sections/{Purpose|Procedures|Risks|Benefits}.json` (draft, final, warnings)
    - `provenance.json` (per-section snippet list with scores + reasons)
    - `facts.procedures.json` (extracted facts + citations)
    - `snippets/{section}.json` (the exact retrieved text used)
    - `metrics.json` (timings, tokens, costs)
    - `ICF_<basename>.docx`
- Registry files (for quick lookup): `db/files.json`, `db/indexes.json`, `db/runs.json`.

## Ingest Pipeline (Deterministic + Hybrid-ready)
1) Parse
- PDF: PyMuPDF (extract text with layout, font size/weight, page numbers).
- DOCX: python-docx (paragraph text, heading levels).
- Emit blocks: `{ page, text, font_size?, bold?, style? }`.

2) Section Segmentation
- Heuristics: heading if larger font/bold/numbered pattern (`1.`, `1.1`, `A.`). Carry `section_path` (e.g., `3 Study Design > 3.2 Procedures`).
- Normalize `heading_norm`: strip numbering, lowercase, canonical mapping (e.g., `Study Design` → `study design`).

3) Chunking
- Target 800–1200 tokens, 100–150 overlap, sentence boundaries preserved; never split table rows (esp. Schedule of Assessments).
- Enrich: prepend `section_path` and local heading to each chunk’s text.
- Stable `chunk_id = sha1(file_id + section_path + page_start + char_offset)`.

4) Role Tagging (LLM only)
- For each chunk, zero-temperature structured output to assign `role_tag ∈ {Purpose, Procedure, Risk, Benefit, Other}`. Cache by `chunk_id + model@ver`.

5) Dual Index (Hybrid)
- Dense: embeddings via LangChain (OpenAI `text-embedding-3-large` or `bge-m3`).
- Sparse: BM25 built in-process over `heading_norm + text`.
- Vector stores: Chroma (preferred for persistence); FAISS optional.
- Store metadata: `{ file_id, index_id, chunk_id, page_span, section_path, heading_norm, role_tag }`.
- Persist index meta: `{ index_id, file_id, store, embed_model@ver, n_chunks, created_at }`.

## Retrieval Strategy (Beyond Simple RAG)
- Routing (allowed headings):
  - Purpose → ["objectives","primary objective","secondary objectives","background","rationale"].
  - Procedures → ["study design","study procedures","treatment plan","schedule of assessments","sample size","enrollment","duration","follow-up"].
  - Risks → ["risks","potential risks","safety","adverse events","warnings"].
  - Benefits → ["benefits","potential benefits"].
- Fixed queries:
  - Purpose: "study objectives and rationale".
  - Procedures: "study design procedures schedule of assessments sample size duration".
  - Risks: "risks side effects adverse events safety".
  - Benefits: "potential benefits".
- Candidate pool:
  - BM25 top 30 + dense top 30. Normalize then fuse: `0.6*sparse + 0.4*dense`. Take fused top 30.
- Filters:
  - Keep chunks with `heading_norm` in allowed list; prefer `role_tag` match; allow `Other` as fallback if recall too low.
- Rerank:
  - Cross-encoder or small LLM rerank using LangChain Runnable. Target final 6–8 snippets per section.
- Trim snippets to 200–300 tokens; carry `{ chunk_id, page_span, section_path, heading_norm, text }`.
- Failure handling:
  - If <4 snippets after filters, relax role_tag, then broaden headings (never include ‘Results/Discussion’ for Procedures).

## Generation (Per Section)
1) Procedures — Facts Extraction (LLM function/tool schema)
- Schema:
  - `n_participants: int|null`
  - `duration: { value:number, unit:"weeks|months|years" } | null`
  - `visit_count: int|null`
  - `arms: string[]`
  - `key_procedures: string[]`
  - `citations`: per field `[{ chunk_id, page }]`
- Rules:
  - Temp 0–0.2. "Use only provided snippets; if absent, return null; cite source chunks." Detect and flag inconsistencies.

2) Writer (All Sections)
- Inputs: final snippets (+ facts for Procedures).
- Style: 8th-grade; define jargon on first use; use modal language (may/might), avoid guarantees.
- Grounding: "Use only provided snippets and facts; if a fact is missing, say ‘not described in the protocol.’"
- Citations in text: After factual sentences, append `[[p. X | Section: <section_path>]]` using the dominant supporting chunk (choose first match or highest score).
- Controls: temp 0.2–0.3; token budget per section.

3) Self-Check (Verifier LLM)
- Input: draft + the exact snippets used.
- Task: sentence-by-sentence verify support, correct citations, fix tone; remove overclaims.
- Output: final section text + per-sentence citation anchors (we’ll compute `sentence_hash`).
- Quality gate: if any factual sentence lacks citation, re-run with stricter instructions; if still failing, mark section with warning.

4) Optional Gap-Closing Loop (≤2 iters, default 1)
- QA scan to identify missing checklist items per section.
- Query synthesis for missing items; focused retrieve; micro-update facts/sentences; self-check again.
- Stop when no new grounded facts or max iters reached.

## DOCX Assembly
- Template placeholders: `{{PURPOSE}}`, `{{PROCEDURES}}`, `{{RISKS}}`, `{{BENEFITS}}`.
- Tooling: `python-docx` (or `docxtpl` if placeholders preferred). Preserve styles; paragraphs only.
- Citations: keep inline bracketed citations in the text; optional: also insert as footnotes (nice-to-have).
- Filename: `ICF_<original_basename>.docx`.

## Observability & Logs
- Provenance JSON per section:
  - Ordered list of used snippets with: `{ chunk_id, page, section_path, heading_norm, fused_score, rerank_reason }`.
- Procedures facts with per-field citations.
- Sentence map: `{ section, sentence_hash, cites: [{chunk_id, page}] }`.
- Timings per step; token/cost ledger per LLM call.

## Error Handling & Edge Cases
- Parsing failures: password-protected PDFs, image-only scans; return actionable error and suggest re-upload. (Optional OCR path later.)
- Low-recall retrieval: progressively relax filters but never accept ‘Results/Discussion’ for Procedures.
- Missing facts: write “not described in the protocol.” without citation for that field.
- Conflicts (e.g., differing N): flag in warnings and choose the most recent or majority; keep conservative text.
- Index drift: if embedding model version changed, invalidate and re-ingest.

## Configuration & Env Vars
- `ARTOS_ENV=dev`
- `ARTOS_DATA_DIR=./data`
- `OPENAI_API_KEY=...` (or compatible key for chosen LLM/embeddings)
- `EMBED_MODEL=text-embedding-3-large` (or `bge-m3`)
- `LLM_MODEL=gpt-4o-mini` (example; choose deterministic, cost-aware)
- Retrieval knobs:
  - `CHUNK_SIZE=1100`, `CHUNK_OVERLAP=120`
  - `HYBRID_K_SPARSE=30`, `HYBRID_K_DENSE=30`, `FUSE_SPARSE=0.6`, `FUSE_DENSE=0.4`, `RERANK_TOP=8`
  - Temps: writer `0.25`, self-check `0.05`, extract `0.1`, gap `0.1`
  - `GAP_LOOP_MAX=1`

## LangChain Usage (Where and How)
- Embeddings: `langchain-openai` (or `langchain-huggingface`) to compute embeddings.
- VectorStore: `langchain_community.vectorstores.Chroma` or `FAISS` with full metadata.
- Retrievers: Compose BM25 + dense retrievers via custom fusion Runnable; implement rerank as a Runnable that scores and reorders docs.
- Chains:
  - `extract_procedure_facts_chain` (structured output / tool calling).
  - `write_section_chain` with prompt + snippets + facts.
  - `self_check_chain` verifying each sentence against snippets.
  - `qa_scan_chain` and `query_synth_chain` for gap loop.
- Runnable config to pass per-call `run_id`, `section` for observability.

## Implementation Steps (Milestones)
1) Boilerplate & scaffolding
- Create Flask app with blueprints; add `data/` dirs; JSON registry helpers.
- Wire config and env vars; add error handlers.

2) Upload
- Implement `/upload` saving files and metadata; validate type/size; compute hash.

3) Ingest & Index
- Implement parse for PDF/DOCX; segmentation + heading normalization; chunking; LLM role-tag chain; embed + upsert to Chroma; build BM25.
- Persist `indexes.json` and stats.

4) Retrieval Service
- Implement hybrid retrieve + filters + rerank + trimming; debug `/search` endpoint.

5) Generation (per section)
- Implement facts extraction (Procedures) chain.
- Implement writer chain with inline citations.
- Implement self-check chain and citation enforcement.
- Implement optional gap loop (max 1 initially).
- Persist per-section artifacts.

6) Assembly & Delivery
- Render DOCX from template; stream via `/runs/{id}/docx`.
- Implement `/runs/{id}` and `/runs/{id}/logs`.

7) QA & Hardening
- Manual tests on provided protocols; verify citations and tone.
- Add timings/tokens/costs; finalize logs structure.

## Testing & Validation
- Golden checks on 3 example protocols:
  - Procedures includes N participants and duration with citations.
  - Risks/Benefits use modal language; citations present.
  - Purpose 1–2 paragraphs, cites Objectives/Rationale.
- Manual retrieval debug via `/search` to confirm top hits.
- Readability spot-check (Flesch-Kincaid or LLM critique) optional.

## Security & Privacy
- Local-only storage; auto-delete files/indexes after N days (configurable) — future.
- Strict file type/size validation; reject password-protected PDFs.
- No PHI expected; optional lightweight PII scan later.
- CORS restricted to front-end origin.

## Future Enhancements
- OCR for scanned PDFs (detect via low text density; Tesseract fallback).
- Better table parsing (Schedule of Assessments) for visit counts.
- Consistency checker for conflicting facts across snippets.
- Artifact bundle endpoint `/runs/{id}/artifacts` (zip of all JSON + DOCX).

## Folder Structure (Target)
- `app/` — Flask app, blueprints, services
  - `services/{vectorstore,retrieval,llm,assembly}.py`
  - `routes/{upload,ingest,generate,runs,search}.py`
  - `utils/{pdf,docx,segment,chunk,ids,io}.py`
- `data/` — runtime artifacts (gitignored)
- `docs/` — this plan, API docs, samples
- `templates/` — DOCX template(s)

## Runbook (Local Dev)
- Python 3.11 recommended.
- Install: `pip install -r requirements.txt` (include Flask, langchain, langchain-openai, chromadb, pymupdf, python-docx, rapidfuzz, tiktoken, pydantic, docxtpl or python-docx)
- Env: set `OPENAI_API_KEY`. Optional: set `ARTOS_DATA_DIR`.
- Run API: `FLASK_APP=app.main:app flask run --reload` (or `python -m app.main`).
- Smoke tests:
  1) POST `/upload` with a sample PDF.
  2) POST `/ingest` with returned `file_id`.
  3) POST `/generate` with `{ file_id, sync: true }`.
  4) GET `/runs/{run_id}` to view sections.
  5) GET `/runs/{run_id}/docx` to download.
  6) GET `/runs/{run_id}/logs` to inspect provenance.

## Prompts (Sketches)
- Role tagger: "Classify this chunk as Purpose/Procedure/Risk/Benefit/Other based ONLY on its content and heading. Output JSON: { role_tag }."
- Facts extraction (Procedures): strict schema with per-field citations; "If absent, return null."
- Writer: "Write the <SECTION> for an informed consent form in simple, 8th-grade language, using ONLY the provided snippets (and facts for Procedures). After each factual sentence, append [[p. X | Section: <section_path>]]. If a required item is missing, say 'not described in the protocol.'"
- Self-check: "For each sentence, verify it is supported by the snippets. If unsupported, remove or rewrite to match the snippet. Ensure proper citation after each factual sentence."

## Definition of Done
- All endpoints respond and persist expected artifacts.
- Sections read clearly, use modal language, and include citations.
- `/runs/{id}/logs` contains retrieval sets, provenance, facts, sentence map, timings, tokens, costs.
- DOCX downloads with populated sections and preserved styles.
