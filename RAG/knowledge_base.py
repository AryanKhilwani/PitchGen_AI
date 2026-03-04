"""
Knowledge Base Loader
Loads and flattens both public and private company data into
a list of documents (text chunks with metadata) for embedding.
"""

import json
from typing import List, Dict


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


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
