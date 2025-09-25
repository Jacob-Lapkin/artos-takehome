from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.state_service import (
    run_dir,
    write_section_artifacts,
    finalize_run,
    get_latest_index_for_file,
    create_run,
)
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.utils.io_utils import ensure_dir, read_json, write_json
from app.services.section_queries import SECTION_QUERIES


class RefinementService:
    """Second-pass refinement over an existing run.

    For each generated section, asks the LLM to suggest up to 3 broad follow-up
    queries targeting missing information, retrieves additional chunks, merges
    with the original snippets, and rewrites the section with the expanded
    context. Persists updated artifacts back under the run directory.
    """

    def __init__(self):
        # Don't initialize services here - create per-thread to avoid contention
        pass

    def _read_run_meta(self, rdir: str) -> Dict[str, Any]:
        return read_json(os.path.join(rdir, "meta.json"), default={}) or {}

    def _read_section_text(self, rdir: str, name: str) -> str:
        data = read_json(os.path.join(rdir, "sections", f"{name}.json"), default={}) or {}
        return (data.get("final_text") or data.get("draft_text") or "").strip()

    def _read_original_hits(self, rdir: str, name: str) -> List[Dict[str, Any]]:
        items = read_json(os.path.join(rdir, "snippets", f"{name}.json"), default=[]) or []
        return items if isinstance(items, list) else []

    def _propose_section_queries(self, section: str, text: str, max_queries: int = 3) -> List[str]:
        # Create per-thread LLM service to avoid shared state issues
        lsvc = LLMService()
        
        prompt = (
            "You are reviewing a drafted Informed Consent Form (ICF) section.\n"
            "Identify important missing information needed for this section, and propose up to 3 broad,\n"
            "library-search style queries that could retrieve relevant passages from a vector database.\n"
            "Keep them general (no patient-specific details). Return ONLY a compact JSON array of strings.\n\n"
            f"Section: {section}\n\nText to review:\n{text}\n\nJSON array only:"
        )
        try:
            resp = lsvc.llm.invoke(prompt)
            content = getattr(resp, "content", str(resp))
            # Extract JSON array
            import re, json as _json
            m = re.search(r"\[[\s\S]*\]", content)
            arr = _json.loads(m.group(0) if m else content)
            if isinstance(arr, list):
                arr = [str(q).strip() for q in arr if str(q).strip()]
                return arr[: max_queries]
        except Exception:
            pass
        return []

    def _merge_hits(self, base: List[Dict[str, Any]], extra: List[Dict[str, Any]], limit: int = 16) -> List[Dict[str, Any]]:
        by_id: Dict[str, Dict[str, Any]] = {}
        for h in base + extra:
            cid = h.get("chunk_id")
            if not cid:
                continue
            if cid not in by_id:
                by_id[cid] = dict(h)
            else:
                # combine scores conservatively
                try:
                    by_id[cid]["score"] = float(by_id[cid].get("score", 0.0)) + float(h.get("score", 0.0))
                except Exception:
                    pass
        merged = sorted(by_id.values(), key=lambda x: x.get("score", 0.0), reverse=True)
        return merged[:limit]

    def _refine_section(self, run_id: str, index_id: str, section: str, rdir: str) -> Tuple[str, Dict[str, Any]]:
        """Refine a single section - designed to run in parallel."""
        # Create per-thread services to avoid shared-state contention
        rsvc = RetrievalService()
        lsvc = LLMService()
        
        current_text = self._read_section_text(rdir, section)
        orig_hits = self._read_original_hits(rdir, section)

        # Ask for follow-up queries
        qs = self._propose_section_queries(section, current_text, max_queries=3)
        print(f"[RUN {run_id}] [Refine:{section}] Proposed queries: {qs}")

        # Retrieve additional hits per query
        extra_hits: List[Dict[str, Any]] = []
        for q in qs:
            try:
                extra_hits.extend(
                    rsvc.search(index_id=index_id, query=q, section=None, mode="dense")
                )
            except Exception as e:
                # ignore retrieval errors for individual queries
                print(f"[RUN {run_id}] [Refine:{section}] Retrieval error for '{q}': {e}")

        # Merge and rewrite
        combined = self._merge_hits(orig_hits, extra_hits, limit=18)
        facts = lsvc.extract_procedure_facts(combined) if section == "Procedures" else None
        draft = lsvc.write_section(section, combined, facts)
        final = lsvc.self_check(section, draft, combined)
        print(f"[RUN {run_id}] [Refine:{section}] Combined hits: {len(combined)}")

        # Persist updated artifacts (overwrite section to reflect refined text)
        write_section_artifacts(
            run_id,
            section,
            snippets=combined,
            draft_text=draft,
            final_text=final,
            warnings=["Refined with follow-up retrieval"],
            facts=facts,
        )

        return section, {"text": final, "queries": qs}

    def refine_run(self, run_id: str) -> Dict[str, Any]:
        rdir = run_dir(run_id)
        meta = self._read_run_meta(rdir)
        if not meta:
            raise RuntimeError("Run not found")
        index_id = meta.get("index_id")
        if not index_id:
            raise RuntimeError("Run missing index_id")

        sections_dir = os.path.join(rdir, "sections")
        if not os.path.isdir(sections_dir):
            raise RuntimeError("Run has no sections to refine")

        # Track queries we asked and any errors
        ref_dir = os.path.join(rdir, "refinement")
        ensure_dir(ref_dir)

        # Get all sections to refine
        sections = []
        for fname in sorted(os.listdir(sections_dir)):
            if fname.endswith(".json"):
                sections.append(os.path.splitext(fname)[0])

        print(f"[RUN {run_id}] Starting parallel refinement for sections: {sections}")

        # Parallel refinement with ThreadPoolExecutor
        updated: Dict[str, Any] = {}
        queries_log: Dict[str, Any] = {}
        
        # Use ThreadPoolExecutor like in your generate route
        with ThreadPoolExecutor(max_workers=min(4, len(sections))) as executor:
            # Submit all section refinement tasks
            futures = [
                executor.submit(self._refine_section, run_id, index_id, sec, rdir) 
                for sec in sections
            ]
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    section, result = future.result()
                    updated[section] = {"text": result["text"]}
                    queries_log[section] = result["queries"]
                except Exception as e:
                    print(f"[RUN {run_id}] Error refining section: {e}")
                    # Continue with other sections even if one fails

        # Save refinement queries log
        write_json(os.path.join(ref_dir, "queries.json"), queries_log)

        finalize_run(run_id, status="refined")
        print(f"[RUN {run_id}] Completed parallel refinement")
        
        return {"run_id": run_id, "status": "refined", "sections": updated, "queries": queries_log}

    def generate_then_refine(self, file_id: str, sections: List[str] | None = None, *, mode: str = "dense", use_section_filter: bool = False) -> Dict[str, Any]:
        """Run the normal generate pipeline first, then refine the same run, returning final refined sections.

        Mirrors the logic in the generate route to avoid HTTP round-trips, then calls refine_run.
        """
        sections = sections or ["Purpose", "Procedures", "Risks", "Benefits"]

        index_id = get_latest_index_for_file(file_id)
        if not index_id:
            raise RuntimeError("No index found for file_id. Run /ingest first.")

        run_id = create_run(file_id, index_id)
        print(f"[RUN {run_id}] Starting generate_then_refine for sections: {sections}")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def run_section(sec: str):
            rsvc = RetrievalService()
            lsvc = LLMService()
            queries = SECTION_QUERIES.get(sec, [])
            if isinstance(queries, str):
                queries = [queries]
            section_arg = sec if use_section_filter else None
            all_hits: Dict[str, Any] = {}
            for q in queries:
                results_list = rsvc.search(index_id=index_id, query=q, section=section_arg, mode=mode)
                for r in results_list:
                    cid = r["chunk_id"]
                    if cid not in all_hits:
                        all_hits[cid] = r
                    else:
                        all_hits[cid]["score"] += r["score"]
            hits = sorted(all_hits.values(), key=lambda x: x["score"], reverse=True)[:12]
            for rank, h in enumerate(hits, start=1):
                try:
                    print(
                        f"[RUN {run_id}] [{sec}]  #{rank:02d} chunk_id={h.get('chunk_id')} page={h.get('page')} "
                        f"heading='{h.get('heading_norm')}' section='{h.get('section_path')}' score={h.get('score')}"
                    )
                except Exception:
                    pass
            facts = lsvc.extract_procedure_facts(hits) if sec == "Procedures" else None
            draft = lsvc.write_section(sec, hits, facts)
            final = lsvc.self_check(sec, draft, hits)
            write_section_artifacts(
                run_id,
                sec,
                snippets=hits,
                draft_text=draft,
                final_text=final,
                warnings=[],
                facts=facts,
            )

        with ThreadPoolExecutor(max_workers=min(4, len(sections))) as ex:
            futs = [ex.submit(run_section, s) for s in sections]
            for f in as_completed(futs):
                _ = f.result()

        finalize_run(run_id, status="succeeded")
        print(f"[RUN {run_id}] Generation complete; starting refinement")
        return self.refine_run(run_id)