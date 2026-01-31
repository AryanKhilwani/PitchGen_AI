from chunker import chunk_text


def build_documents(public_data: dict, private_data: dict):
    documents = []

    # ---------- PUBLIC DATA ----------
    for _, page in public_data["pages"].items():
        blocks = page.get("content_blocks", {})
        text = blocks.get("main") or blocks.get("full", "")

        for chunk in chunk_text(text):
            documents.append(
                {
                    "text": chunk,
                    "metadata": {
                        "source": "public",
                        "url": page["url"],
                        "title": page["title"],
                        "method": page.get("method"),
                    },
                }
            )

    # ---------- PRIVATE DATA ----------
    for filename, filedata in private_data["files"].items():
        if filedata["type"] == "markdown":
            for section, content in filedata["content"].items():
                for chunk in chunk_text(content):
                    documents.append(
                        {
                            "text": f"{section}\n{chunk}",
                            "metadata": {
                                "source": "private",
                                "file": filename,
                                "section": section,
                            },
                        }
                    )

        elif filedata["type"] == "excel":
            for sheet, table in filedata["content"].items():
                rows = table["rows"]
                text = "\n".join(str(r) for r in rows)
                for chunk in chunk_text(text):
                    documents.append(
                        {
                            "text": f"{sheet}\n{chunk}",
                            "metadata": {
                                "source": "private",
                                "file": filename,
                                "sheet": sheet,
                            },
                        }
                    )

    return documents
