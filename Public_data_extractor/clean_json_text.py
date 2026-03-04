import json
import hashlib
from collections import defaultdict


def flatten_pages(pages_dict):
    """Recursively flattens the nested children structure into a single list of pages."""
    flat_list = []
    for path, data in pages_dict.items():
        flat_list.append({"url": data.get("url"), "text": data.get("text", "")})
        if "children" in data and data["children"]:
            flat_list.extend(flatten_pages(data["children"]))
    return flat_list


def generate_hash(text):
    """Generates a quick MD5 hash for a normalized string."""
    # Normalize by stripping whitespace and lowercasing to catch near-exact matches
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def clean_syntactic_data(raw_json):
    # 1. Flatten the hierarchy
    pages = flatten_pages(raw_json.get("pages", {}))
    total_pages = len(pages)

    # 2. Build Document Frequency (DF) for every line
    # This detects navbars and footers because they appear on almost every page.
    line_df = defaultdict(int)
    for page in pages:
        # Use a set to count appearances per document, not total occurrences
        unique_lines = set(
            [line.strip() for line in page["text"].split("\n") if line.strip()]
        )
        for line in unique_lines:
            line_df[line] += 1

    # Define a threshold: If a line appears in > 60% of URLs, it is boilerplate
    df_threshold = max(2, int(total_pages * 0.6))

    # 3. Filter and Deduplicate
    global_seen_hashes = set()
    cleaned_data = []

    for page in pages:
        clean_paragraphs = []
        raw_lines = page["text"].split("\n")

        current_paragraph = []

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Drop the line if it's cross-document boilerplate
            if line_df[stripped] >= df_threshold:
                continue

            current_paragraph.append(stripped)

            # Treat structural breaks (like double newlines in original text) as paragraph boundaries
            # For simplicity, let's group every 3-4 lines or split on natural sentence endings.
            # Here we just chunk lines that survived the boilerplate filter.
            if stripped.endswith(".") or len(current_paragraph) > 3:
                paragraph_text = " ".join(current_paragraph)
                p_hash = generate_hash(paragraph_text)

                # Check for exact paragraph duplicates (handles the homepage repetition)
                if p_hash not in global_seen_hashes:
                    global_seen_hashes.add(p_hash)
                    clean_paragraphs.append(paragraph_text)

                current_paragraph = []  # Reset for next chunk

        # Catch any trailing text
        if current_paragraph:
            paragraph_text = " ".join(current_paragraph)
            p_hash = generate_hash(paragraph_text)
            if p_hash not in global_seen_hashes:
                global_seen_hashes.add(p_hash)
                clean_paragraphs.append(paragraph_text)

        if clean_paragraphs:
            cleaned_data.append(
                {"url": page["url"], "clean_text": "\n\n".join(clean_paragraphs)}
            )

    return cleaned_data


# Assuming your provided JSON is stored in a variable `scraped_data`
# cleaned_output = clean_syntactic_data(scraped_data)
# print(json.dumps(cleaned_output, indent=2))
