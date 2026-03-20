"""
Knowledge Base Loader
Loads and flattens both public and private company data into
a list of documents (text chunks with metadata) for embedding.

v2: each document's metadata now includes a `content_hints` list that
    tells downstream agents what visual structures the section can feed
    (e.g. "timeline", "process_steps", "comparison", "metrics", etc.).
    No LLM call is needed — hints are inferred from section names and
    lightweight text patterns.
"""

import json
import re
from typing import List, Dict


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


# ── Semantic hint inference (no LLM needed) ──────────────────────────────

# Section-name keywords → content hint labels
_SECTION_HINT_MAP: dict[str, list[str]] = {
    # Timeline / chronology
    "milestone": ["timeline"],
    "history": ["timeline"],
    "journey": ["timeline"],
    "timeline": ["timeline"],
    "founded": ["timeline"],
    # Process / steps
    "process": ["process_steps"],
    "workflow": ["process_steps"],
    "manufacturing": ["process_steps"],
    "supply chain": ["process_steps", "linear_chain"],
    "value chain": ["linear_chain"],
    # Comparison / SWOT
    "swot": ["comparison"],
    "strength": ["comparison"],
    "weakness": ["comparison"],
    "opportunity": ["comparison"],
    "threat": ["comparison"],
    "competitive": ["comparison"],
    "peer": ["comparison"],
    "benchmark": ["comparison"],
    # Metrics / KPIs
    "financial": ["metrics", "time_series"],
    "revenue": ["metrics", "time_series"],
    "profit": ["metrics", "time_series"],
    "performance": ["metrics"],
    "key metric": ["metrics"],
    "kpi": ["metrics"],
    "operational indicator": ["metrics"],
    # Relationships / hierarchy
    "shareholder": ["composition", "tabular"],
    "ownership": ["composition"],
    "management": ["hierarchy"],
    "leadership": ["hierarchy"],
    "team": ["hierarchy"],
    "board": ["hierarchy"],
    "organization": ["hierarchy"],
    # Portfolio / products
    "product": ["portfolio"],
    "service": ["portfolio"],
    "portfolio": ["portfolio"],
    "offering": ["portfolio"],
    "segment": ["portfolio", "composition"],
    # Geography / network
    "global": ["geography"],
    "location": ["geography"],
    "presence": ["geography"],
    "export": ["geography"],
    "client": ["relationship_list"],
    "partner": ["relationship_list"],
    "customer": ["relationship_list"],
    # Tabular
    "certification": ["tabular"],
    "rating": ["tabular"],
    "award": ["tabular"],
}

# Text-body patterns (compiled once)
_DATE_PATTERN = re.compile(
    r"\b(FY\d{2,4}|Q[1-4]\s*FY\d{2,4}|\d{4}[-–]\d{2,4}|\b(?:19|20)\d{2}\b)",
    re.IGNORECASE,
)
_NUMBERED_STEP = re.compile(r"(?:^|\n)\s*(?:\d+[.)]\s|step\s+\d)", re.IGNORECASE)
_TABLE_ROW = re.compile(r"\|.*\|.*\|")
_PERCENTAGE = re.compile(r"\d+\.?\d*\s*%")


def _infer_content_hints(section_name: str, text: str) -> list[str]:
    """Return a list of semantic hint strings for a document chunk.

    Uses section name keywords + lightweight regex on the text body.
    Cheap enough to run at indexing time for every chunk.
    """
    hints: set[str] = set()
    section_lower = section_name.lower()

    # 1. Section-name keyword matching
    for keyword, labels in _SECTION_HINT_MAP.items():
        if keyword in section_lower:
            hints.update(labels)

    # 2. Text-body pattern matching
    date_matches = _DATE_PATTERN.findall(text)
    if len(date_matches) >= 3:
        hints.add("time_series")
    if len(date_matches) >= 2 and any(
        w in section_lower for w in ("milestone", "history", "journey", "timeline")
    ):
        hints.add("timeline")

    if _NUMBERED_STEP.search(text):
        hints.add("process_steps")

    table_rows = _TABLE_ROW.findall(text)
    if len(table_rows) >= 2:
        hints.add("tabular")

    pct_matches = _PERCENTAGE.findall(text)
    if len(pct_matches) >= 3:
        hints.add("composition")

    return sorted(hints) if hints else ["general"]


def flatten_public_data(data: dict) -> List[Dict]:
    """
    Public data structure:
    {
      "Category": {
        "subcategory_key": ["fact1", "fact2", ...]
      }
    }
    Each subcategory becomes one document with all its facts joined.
    """
    documents = []

    for category, subcategories in data.items():
        if not isinstance(subcategories, dict):
            continue

        for subcat_key, facts in subcategories.items():
            if not isinstance(facts, list) or not facts:
                continue

            # Readable section title
            section_title = subcat_key.replace("_", " ").title()
            text = f"[{category} > {section_title}]\n" + "\n".join(
                f"- {f}" for f in facts
            )

            documents.append(
                {
                    "text": text,
                    "metadata": {
                        "source": "public",
                        "category": category,
                        "section": subcat_key,
                        "section_title": section_title,
                        "content_hints": _infer_content_hints(section_title, text),
                    },
                }
            )

    return documents


def flatten_private_data(data: dict) -> List[Dict]:
    """
    Private data structure:
    {
      "files": {
        "filename.md": {
          "type": "markdown",
          "content": {
            "Section Name": "text or markdown content",
            ...
          }
        }
      }
    }
    Each section becomes one document. Large sections (financials) are kept whole
    since they form coherent units useful for investment analysis.
    """
    documents = []

    files = data.get("files", {})
    for filename, file_data in files.items():
        content = file_data.get("content", {})
        company_name = filename.replace("-OnePager.md", "").replace("-", " ").title()

        for section_name, section_text in content.items():
            if not section_text or section_text == "Not Available":
                continue

            text_str = str(section_text)

            # Skip very short or empty sections
            if len(text_str.strip()) < 20:
                continue

            # For very large sections (financials), split into manageable chunks
            if len(text_str) > 3000:
                chunks = _split_large_section(text_str, section_name, max_chars=2500)
                for i, chunk in enumerate(chunks):
                    header = f"[{company_name} > {section_name} (Part {i+1})]\n"
                    documents.append(
                        {
                            "text": header + chunk,
                            "metadata": {
                                "source": "private",
                                "company": company_name,
                                "section": section_name,
                                "part": i + 1,
                                "filename": filename,
                                "content_hints": _infer_content_hints(
                                    section_name, chunk
                                ),
                            },
                        }
                    )
            else:
                header = f"[{company_name} > {section_name}]\n"
                documents.append(
                    {
                        "text": header + text_str,
                        "metadata": {
                            "source": "private",
                            "company": company_name,
                            "section": section_name,
                            "filename": filename,
                            "content_hints": _infer_content_hints(
                                section_name, text_str
                            ),
                        },
                    }
                )

    return documents


def _split_large_section(
    text: str, section_name: str, max_chars: int = 2500
) -> List[str]:
    """
    Split large text sections (like financial tables) by lines,
    keeping chunks under max_chars while respecting line boundaries.
    """
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(line)
        current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def build_knowledge_base(
    public_data_path: str = "../Public_data_cleaner/outputs/final_structured_data.json",
    private_data_path: str = "../Private_data_extractor/outputs/private_data_bundle.json",
) -> List[Dict]:
    """
    Main entry point: loads both data sources, flattens into documents.
    Returns list of {"text": str, "metadata": dict}
    """
    documents = []

    # Load public data
    print("Loading public data...")
    try:
        public_data = load_json(public_data_path)
        public_docs = flatten_public_data(public_data)
        documents.extend(public_docs)
        print(f"  -> {len(public_docs)} documents from public data")
    except FileNotFoundError:
        print(f"  -> Public data not found at {public_data_path}, skipping.")

    # Load private data
    print("Loading private data...")
    try:
        private_data = load_json(private_data_path)
        private_docs = flatten_private_data(private_data)
        documents.extend(private_docs)
        print(f"  -> {len(private_docs)} documents from private data")
    except FileNotFoundError:
        print(f"  -> Private data not found at {private_data_path}, skipping.")

    print(f"Total knowledge base: {len(documents)} documents")
    return documents
