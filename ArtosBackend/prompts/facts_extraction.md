# Procedures Facts Extraction Prompt (Placeholder)

Task: Extract structured facts from provided snippets ONLY.
- Fields: n_participants, duration {value, unit}, visit_count, arms[], key_procedures[]
- Include per-field citations: [{chunk_id, page}]
- If not found, return null for that field.
- Temperature low; do not infer beyond given text.

