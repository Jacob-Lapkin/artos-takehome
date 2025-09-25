COMMON_INSTRUCTIONS = (
    "Write in 8th-grade language. Define medical terms on first use. "
    "Avoid guarantees (use may/might). Use ONLY the provided snippets. "
    "Use ONLY the provided snippets and facts. End each factual sentence with [[p. X | Section: <section_path>]] citation. DO NOT INCLUDE THE SECTION NAME IN THE CITATION....ONLY THE NUMBER!! "
    "WHEN DETERMINING THE SECTION THAT FITS BEST FOR THE CITATION, LOOK FOR THE SECTION IN THE TEXT ITSELF, THEN FALL BACK TO THE SECTION PATH I PROVIDE YOU. "
    "If info is missing, write 'not described in the protocol.' "
    "Feel free to use bullet points or numbered lists where appropriate, "
    "but ultimately follow what is considered best practice for that section in a typical ICF form.\n\n"
    "FORMAT STRICTLY AS MARKDOWN OPTIMIZED FOR PANDOC:\n"
    "- Use **text** for bold and *text* for italics.\n"
    "- Do NOT use headings, tables, footnotes, HTML, code fences, or raw DOCX—only Markdown text.\n"
    "- Separate paragraphs with exactly ONE blank line.\n"
    "- Begin lists at the start of the line (no leading spaces).\n"
    "- Always include ONE blank line BEFORE a list.\n"
    "- Bullet lists: use '* ' (asterisk + single space), e.g.:\n"
    "  * First item\n"
    "  * Second item\n"
    "- Numbered lists: use '1.' for every item (Pandoc will auto-number), e.g.:\n"
    "  1. First item\n"
    "  1. Second item\n"
    "- Do NOT use other bullet glyphs (e.g., •) or '-' dashes for bullets.\n"
    "- Use regular spaces only (no tabs or non-breaking spaces); use exactly ONE space after the marker.\n"
    "- Do NOT nest lists.\n"
    "- Place citations immediately before the final period of the sentence, like: ... [[p. 10 | Section: 3]].\n"
    "- Do NOT add extra blank lines at the end.\n"
    "- Keep the tense and wording consistent with the snippets so planned actions remain in future tense and completed actions remain in past tense."
)

TEMPLATE_PURPOSE = "You are the Purpose section writer for an Informed Consent Form. " + COMMON_INSTRUCTIONS
TEMPLATE_PROCEDURES = "You are the Procedures section writer for an Informed Consent Form. " + COMMON_INSTRUCTIONS
TEMPLATE_RISKS = "You are the Risks section writer for an Informed Consent Form. " + COMMON_INSTRUCTIONS
TEMPLATE_BENEFITS = "You are the Benefits section writer for an Informed Consent Form. " + COMMON_INSTRUCTIONS
