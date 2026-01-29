import re


def extract_md(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = {}
    current_title = "Untitled"
    sections[current_title] = []

    for line in content.splitlines():
        header = re.match(r"^(#{1,6})\s+(.*)", line)
        if header:
            current_title = header.group(2).strip()
            sections[current_title] = []
        else:
            sections[current_title].append(line)

    final_sections = {
        title: "\n".join(lines).strip()
        for title, lines in sections.items()
        if "\n".join(lines).strip()
    }

    return {"type": "markdown", "content": final_sections}
