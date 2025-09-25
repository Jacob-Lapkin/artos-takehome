# assembly_service_pandoc.py
from __future__ import annotations

import os
import re
from typing import Dict, List
from os.path import basename

from app.config import Config
from app.utils.io_utils import read_json, ensure_dir

try:
    import pypandoc
except ImportError:
    raise ImportError(
        "pypandoc is required. Install with `pip install pypandoc` and make sure the Pandoc binary is installed."
    )

# --- Inline ICF template scaffold ---
# Keys are the visible DOCX headings (level-2 "##" in Markdown).
# Values:
#   - "Purpose" / "Procedures" / "Risks" / "Benefits"  -> insert generated text
#   - any other string                                -> keep as static boilerplate
TEMPLATE_SECTIONS: Dict[str, str] = {
    "Section 1. Purpose of the Research": "Purpose",
    "Section 2. Procedures": "Procedures",
    "Section 3. Time Duration of the Procedures and Study": "This study will last … (static text)",
    "Section 4. Discomforts and Risks": "Risks",
    "Section 5. Potential Benefits": "Benefits",
    "Section 6. Statement of Confidentiality": (
        "This section contains information about the confidentiality of information collected during this study. "
        "Note that, as applicable, a description of this clinical trial may become available on http:///www.ClinicalTrials.gov, "
        "as required by U.S. Law. This website will not include information that can identify you. At most, the website will "
        "include a summary of the results. You can search the website at any time.\n\n"
        "6a. Privacy and confidentiality measures\n\n"
        "6b. The use of private health information"
    ),
    "Section 7. Costs for Participation": "7a. Costs:\n\n7b. Treatment and compensation for injury:\n\n",
    "Section 8. Compensation for Participation": "You may receive … (static text)",
    "Section 9. Research Funding": "This research is funded by …",
    "Section 10. Voluntary Participation": (
        "Taking part in this research study is completely voluntary. You do not have to participate in this research. "
        "If you choose to take part, you have the right to stop at any time. If you decide not to participate or if you decide "
        "to stop taking part in the research at a later date, there will be no penalty or loss of benefits to which you are otherwise entitled. "
        "Note that the Principal Investigator of this study may take you out of the research study at their sole discretion. Some reasons for this may include: "
        "1) you did not follow the study procedures, 2) the risks of potential harm from the study became too high, or 3) the study was concluded earlier than expected. "
        "The Principal Investigator may have separate reasons instead of, or in addition to, those listed. If you do not sign this form, you will not receive research-related interventions."
    ),
    "Section 11. Contact Information for Questions or Concerns": (
        "[Check this section carefully. Contact information may need to be manually filled in.]\n\n"
        "You have the right to ask any questions you may have about this research study. If you have questions, concerns, or complaints, "
        "or believe you may have developed an injury related to this research, contact the study team immediately. The study team’s contact information is below:\n\n"
        "Contact:\nPhone:\nEmail:\n\n"
        "If you have questions regarding your rights as a research participant or you have concerns or general questions about the research or, as applicable, "
        "about your privacy and the use of your personal health information, contact the applicable Institutional Review Board. Contact information is listed below:\n\n"
        "Contact:\nPhone:\nEmail:"
    ),
    "Signature and Consent/Permission to be in the Research": (
        "Before making the decision regarding enrollment in this research you should have:\n"
        "* Discussed this study with an investigator,\n"
        "* Reviewed the information in this form, and\n"
        "* Had the opportunity to ask any questions you may have.\n\n"
        "Your signature below means that you have received this information, have asked the questions you currently have about the research and those questions have been answered. "
        "You will receive a copy of the signed and dated form to keep for future reference.\n\n"
        "**Participant:** By signing this consent form, you indicate that you are voluntarily choosing to take part in this research.\n\n"
        "_____________________________\t______\t______\t_____________\n"
        "Signature of Participant\tDate\tTime\tPrinted Name\n\n"
        "**Participant’s Legally Authorized Representative:** By signing below, you indicate that you give permission for the participant to take part in this research.\n\n"
        "____________________________\t______\t______\t____________\n"
        "Signature of Participant’s Legally Authorized Representative\tDate\tTime\tPrinted Name\n"
        "(Signature of Participant’s Legally Authorized Representative is required for people unable to give consent for themselves.)\n\n"
        "Description of the Legally Authorized Representative’s Authority to Act for Participant:\n"
        "_____________________________\n\n"
        "**Person Explaining the Research:** Your signature below means that you have explained the research to the participant/participant representative and have answered any questions he/she has about the research.\n\n"
        "____________________________\t______\t______\t___________\n"
        "Signature of person who explained this research\tDate\tTime\tPrinted Name\n\n"
        "Only approved investigators for this research may explain the research and obtain informed consent.\n\n"
        "A witness or witness/translator is required when the participant cannot read the consent document, and it was read or translated."
    ),
}

NBSP = "\u00A0"
GEN_SECTIONS = {"Purpose", "Procedures", "Risks", "Benefits"}


class AssemblyService:
    """
    DOCX assembly using Pandoc with Markdown normalization.

    Flow:
      - Load section JSON (final_text or draft_text).
      - Normalize Markdown so Pandoc reliably recognizes bullets/numbers.
      - Stitch into a single Markdown doc using TEMPLATE_SECTIONS (mix of static + generated).
      - Convert to DOCX via Pandoc, optionally using templates/reference.docx to control styles.
    """

    def __init__(self, cfg: Config = Config):
        self.cfg = cfg
        # reference_doc controls styles (not content)
        self.reference_doc = os.path.join(os.getcwd(), "templates", "reference.docx")

    # ---------------------------
    # Paths & IO
    # ---------------------------
    def _run_dir(self, run_id: str) -> str:
        return os.path.join(self.cfg.RUNS_DIR, run_id)

    def _load_sections_text(self, run_id: str) -> Dict[str, str]:
        """
        Load final_text (or draft_text) for each logical generated section from:
          runs/<run_id>/sections/{Purpose,Procedures,Risks,Benefits}.json
        Strip any leading 'Section:' boilerplate emitted by upstream tools.
        """
        rdir = self._run_dir(run_id)
        sections_dir = os.path.join(rdir, "sections")
        out: Dict[str, str] = {}

        for key in GEN_SECTIONS:
            path = os.path.join(sections_dir, f"{key}.json")
            data = read_json(path, default=None)
            if isinstance(data, dict):
                text = (data.get("final_text") or data.get("draft_text") or "").strip()
                if text.startswith("Section:"):
                    lines = text.splitlines()
                    if len(lines) > 2:
                        text = "\n".join(lines[2:]).strip()
                out[key] = text
            else:
                out[key] = ""
        return out

    # ---------------------------
    # Text normalization helpers
    # ---------------------------
    def _simplify_citations(self, text: str) -> str:
        """
        Normalize citations while preserving page and section number, e.g. [[p. 12 | Section: 3]].
        """
        def repl(m: re.Match) -> str:
            inner = m.group(1)
            # keep [[p. X | Section: Y]] or [[p. X]]
            if re.match(r"p\.\s*\d+(\s*\|\s*Section:\s*[\d\.]+)?", inner):
                return f"[[{inner.strip()}]]"
            pm = re.search(r"p\.\s*(\d+)", inner)
            return f"[[p. {pm.group(1)}]]" if pm else m.group(0)
        return re.sub(r"\[\[(.*?)\]\]", repl, text or "")

    def _normalize_markdown_lists(self, text: str) -> str:
        """
        Make list markers conform to Markdown rules so Pandoc always recognizes them.
        """
        if not text:
            return ""
        text = text.replace(NBSP, " ").replace("\t", "    ")
        lines = text.splitlines()

        norm: List[str] = []
        bullet_rx = re.compile(r'^(\s*)([*\-•])\s+(.*)$')
        number_rx = re.compile(r'^(\s*)(\d+)[\.\)]\s+(.*)$')
        bullet_space_rx = re.compile(r'^(\s*)\*\s{2,}(.*)$')
        number_space_rx = re.compile(r'^(\s*)(\d+)\.\s{2,}(.*)$')

        for ln in lines:
            m = bullet_rx.match(ln)
            if m:
                indent, _mark, rest = m.groups()
                ln = f"{indent}* {rest}"
            else:
                m2 = number_rx.match(ln)
                if m2:
                    indent, num, rest = m2.groups()
                    ln = f"{indent}{num}. {rest}"
            m3 = bullet_space_rx.match(ln)
            if m3:
                indent, rest = m3.groups()
                ln = f"{indent}* {rest}"
            m4 = number_space_rx.match(ln)
            if m4:
                indent, num, rest = m4.groups()
                ln = f"{indent}{num}. {rest}"
            norm.append(ln.rstrip())

        def is_list_line(s: str) -> bool:
            return bool(re.match(r'^\s*(\*|\d+\.)\s+\S', s))

        result: List[str] = []
        i = 0
        while i < len(norm):
            if is_list_line(norm[i]):
                if result and result[-1].strip() != "":
                    result.append("")
                while i < len(norm) and is_list_line(norm[i]):
                    result.append(norm[i])
                    i += 1
                if i < len(norm) and norm[i].strip() != "":
                    result.append("")
            else:
                result.append(norm[i])
                i += 1

        cleaned: List[str] = []
        for s in result:
            if s.strip() == "":
                if cleaned and cleaned[-1] == "":
                    continue
                cleaned.append("")
            else:
                cleaned.append(s)

        return "\n".join(cleaned).strip()

    # ---------------------------
    # Public API
    # ---------------------------
    def render_docx(self, run_id: str) -> str:
        # Load generated section texts
        texts = self._load_sections_text(run_id)

        # Build Markdown mixing static template + generated sections
        md_parts: List[str] = []
        for heading, content in TEMPLATE_SECTIONS.items():
            if content in GEN_SECTIONS:
                raw = texts.get(content, "") or ""
                raw = self._simplify_citations(raw)
                body = self._normalize_markdown_lists(raw)
            else:
                body = content or ""
            md_parts.append(f"## {heading}\n\n{body}\n")

        full_md = "\n\n".join(md_parts).strip()

        # Output path prep
        meta = read_json(os.path.join(self._run_dir(run_id), "meta.json"), default={}) or {}
        file_id = meta.get("file_id") or "file"
        files_db = read_json(os.path.join(self.cfg.DB_DIR, "files.json"), default={}) or {}
        fname = files_db.get(file_id, {}).get("filename") or f"{file_id}.docx"
        base, _ = os.path.splitext(basename(fname))

        out_dir = self._run_dir(run_id)
        ensure_dir(out_dir)
        out_path = os.path.join(out_dir, f"ICF_{base}.docx")

        # Pandoc conversion (reference_doc applies styles only)
        extra_args: List[str] = []
        if os.path.exists(self.reference_doc):
            extra_args.append(f"--reference-doc={self.reference_doc}")

        pypandoc.convert_text(
            full_md,
            "docx",
            format="markdown+lists_without_preceding_blankline",
            outputfile=out_path,
            extra_args=extra_args,
        )

        return out_path
