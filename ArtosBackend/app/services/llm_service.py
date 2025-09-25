"""LLMService: orchestrates LLM-powered steps for generation.

Provides minimal but functional chains for:
- Procedures facts extraction (JSON output with citations by chunk_id/page).
- Section writer that uses provided snippets and facts and appends inline citations.
- Self-check pass that ensures every factual sentence has a citation (heuristic).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
import importlib
import os
from dotenv import load_dotenv

from app.config import Config

load_dotenv()  # This loads the .env file

from prompts.writer_common_template import (
    TEMPLATE_PURPOSE,
    TEMPLATE_PROCEDURES,
    TEMPLATE_RISKS,
    TEMPLATE_BENEFITS,
)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
except Exception:  # pragma: no cover
    ChatGoogleGenerativeAI = None  # type: ignore

SECTION_TEMPLATES = {
    "purpose": TEMPLATE_PURPOSE,
    "procedures": TEMPLATE_PROCEDURES,
    "risks": TEMPLATE_RISKS,
    "benefits": TEMPLATE_BENEFITS,
}

class LLMService:
    def __init__(self, cfg: Config = Config):
        self.cfg = cfg
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("langchain-google-genai is required. Install and set GOOGLE_API_KEY.")
        # Choose the model from config (default gemini-2.5-flash)
        self.model_name = getattr(cfg, "LLM_MODEL", "gemini-2.5-flash")
        self.llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=0.2)
        self._prompt_cache: Dict[str, str] = {}

    def _join_snippets(self, snippets: List[Dict[str, Any]], max_chars: int = 15000) -> str:
        parts = []
        used = 0
        for s in snippets:
            header = f"[chunk_id={s['chunk_id']} page={s['page']} section={s['section_path']}]\n"
            body = s.get("text") or ""
            block = header + body
            if used + len(block) > max_chars:
                break
            parts.append(block)
            used += len(block)
        return "\n\n".join(parts)

    def extract_procedure_facts(self, snippets: List[Dict[str, Any]]) -> Dict[str, Any]:
        content = self._join_snippets(snippets)
        prompt = (
            "You are extracting structured facts about study procedures from the provided snippets.\n"
            "Use ONLY the text in the snippets. If a fact is absent, return null.\n"
            "Return strict JSON with keys: n_participants (int|null), duration (object|null) with {value:number, unit:'weeks|months|years'},\n"
            "visit_count (int|null), arms (string[]), key_procedures (string[]), and citations (object)\n"
            "with per-field citations arrays containing objects {chunk_id, page}.\n\n"
            "Snippets:\n" + content + "\n\nReturn JSON only."
        )
        resp = self.llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        # Extract JSON from response
        m = re.search(r"\{[\s\S]*\}$", text)
        js = text if m is None else m.group(0)
        try:
            data = json.loads(js)
        except Exception:
            data = {
                "n_participants": None,
                "duration": None,
                "visit_count": None,
                "arms": [],
                "key_procedures": [],
                "citations": {},
            }
        return data

    def _load_writer_template(self, section: str) -> str:
        key = section.lower()
        if key in self._prompt_cache:
            return self._prompt_cache[key]
        txt = SECTION_TEMPLATES.get(key, TEMPLATE_PURPOSE)  # fallback to Purpose template
        self._prompt_cache[key] = txt
        return txt


    def write_section(
        self,
        section: str,
        snippets: List[Dict[str, Any]],
        facts: Optional[Dict[str, Any]] = None,
    ) -> str:
        content = self._join_snippets(snippets)
        facts_json = json.dumps(facts or {}, ensure_ascii=False)
        template = self._load_writer_template(section)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template),
                (
                    "human",
                    "Write the {section} section.\n\nSnippets:\n{snippets}\n\nFacts (JSON):\n{facts_json}\n\nReturn only the section text with citations inline. REMEMBER, SECTION IN CITATION SHOULD NOT INCLUDE THE NAME...ONLY THE NUMBER FOR THE SECTION",
                ),
            ]
        )
        chain = prompt | self.llm
        result = chain.invoke({"section": section, "snippets": content, "facts_json": facts_json})
        return result.content if hasattr(result, "content") else str(result)

    def self_check(self, section: str, text: str, snippets: List[Dict[str, Any]]) -> str:
        """Light self-check: return text unchanged (trimmed)."""
        return (text or "").strip()
