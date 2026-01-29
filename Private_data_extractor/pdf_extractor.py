# import pdfplumber
# import statistics


# def extract_pdf(path: str) -> dict:
#     pages = {}

#     with pdfplumber.open(path) as pdf:
#         for i, page in enumerate(pdf.pages):
#             words = page.extract_words(
#                 use_text_flow=True, extra_attrs=["size", "fontname", "top"]
#             )

#             if not words:
#                 pages[f"page_{i+1}"] = {"detected_titles": [], "text": ""}
#                 continue

#             # Compute median font size (body text proxy)
#             font_sizes = [w["size"] for w in words]
#             median_size = statistics.median(font_sizes)

#             detected_titles = []
#             body_lines = []

#             for w in words:
#                 text = w["text"].strip()

#                 # Heuristic: larger than body + near top
#                 if w["size"] > median_size * 1.3 and w["top"] < 120 and len(text) < 80:
#                     detected_titles.append(text)
#                 else:
#                     body_lines.append(text)

#             pages[f"page_{i+1}"] = {
#                 "detected_titles": list(dict.fromkeys(detected_titles)),
#                 "text": " ".join(body_lines),
#             }

#     return {"type": "pdf", "content": pages}


import fitz


def extract_pdf(path: str) -> dict:
    doc = fitz.open(path)
    pages = {}

    for i, page in enumerate(doc):
        blocks = page.get_text("blocks")  # layout-aware
        text_blocks = []

        for b in blocks:
            if b[6] == 0:  # text block
                text_blocks.append(b[4].strip())

        pages[f"page_{i+1}"] = {"text": "\n".join(text_blocks)}

    return {"type": "pdf", "content": pages}
