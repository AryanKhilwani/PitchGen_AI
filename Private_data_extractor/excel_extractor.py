import pandas as pd


def extract_excel(path: str) -> dict:
    xls = pd.ExcelFile(path)
    sheets = {}

    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        sheets[sheet] = {
            "columns": list(df.columns),
            "rows": df.fillna("").values.tolist(),
        }

    return {"type": "excel", "content": sheets}
