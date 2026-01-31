import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalize extracted text while preserving structure.
    Suitable for RAG, KG construction, and LLM consumption.

    What it DOES:
    - Normalizes unicode characters
    - Removes junk whitespace
    - Preserves paragraph / line structure
    - Removes excessive blank lines

    What it DOES NOT:
    - Summarize or rewrite
    - Remove headings
    - Destroy newlines
    """

    if not text:
        return ""

    # Normalize unicode (e.g. smart quotes, weird spaces)
    text = unicodedata.normalize("NFKC", text)

    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse horizontal whitespace (spaces, tabs)
    text = re.sub(r"[ \t]+", " ", text)

    # Remove trailing spaces on each line
    text = "\n".join(line.rstrip() for line in text.splitlines())

    # Collapse excessive blank lines (keep max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
