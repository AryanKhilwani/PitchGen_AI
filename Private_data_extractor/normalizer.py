import re
from universal_loader import PrivateDataLoader
import json
import os


class PrivateDataNormalizer:
    def run(self, raw_index: list[dict]) -> dict:
        financial = []
        operations = []
        products = []
        customers = []
        qualitative = []

        for item in raw_index:
            text = item["text"].lower()

            if re.search(r"revenue|turnover|ebitda|cagr", text):
                financial.append(item)

            elif re.search(r"plant|facility|manufacturing|capacity", text):
                operations.append(item)

            elif re.search(r"product|portfolio|offering", text):
                products.append(item)

            elif re.search(r"customer|oem|client", text):
                customers.append(item)

            else:
                qualitative.append(item)

        return {
            "financial_metrics": financial,
            "operational_metrics": operations,
            "products": products,
            "customers": customers,
            "other_notes": qualitative,
        }


if __name__ == "__main__":
    file_paths = ["Company Data/automotive-kalyani-forge/Kalyani Forge-OnePager.md"]

    loader = PrivateDataLoader()
    private_data_bundle = loader.run(file_paths)

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/private_data_bundle.json", "w", encoding="utf-8") as f:
        json.dump(private_data_bundle, f, indent=2, ensure_ascii=False)

    print("✅ Private data bundle saved")
