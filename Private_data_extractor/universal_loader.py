from pathlib import Path
from excel_extractor import extract_excel
from pdf_extractor import extract_pdf
from doc_extractor import extract_doc
from md_extractor import extract_md
import os


class PrivateDataLoader:
    def run(self, file_paths: list[str]) -> dict:
        files = {}

        for path in file_paths:
            ext = Path(path).suffix.lower()
            file_name = Path(path).name

            if ext in [".xls", ".xlsx"]:
                data = extract_excel(path)
            elif ext == ".pdf":
                data = extract_pdf(path)
            elif ext in [".doc", ".docx"]:
                data = extract_doc(path)
            elif ext in [".md", ".markdown"]:
                data = extract_md(path)
            else:
                continue

            files[file_name] = {
                **data,
                "metadata": {"path": path, "size_bytes": os.path.getsize(path)},
            }

        return {"files": files}
