import docx


def extract_doc(path: str) -> dict:
    doc = docx.Document(path)
    paragraphs = {}

    for i, para in enumerate(doc.paragraphs):
        paragraphs[f"para_{i+1}"] = para.text

    return {"type": "doc", "content": paragraphs}
