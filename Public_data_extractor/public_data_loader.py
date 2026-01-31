from website_discovery import find_company_website
from website_crawler import crawl_website
from hierarchy_builder import build_page_hierarchy
from datetime import datetime, timezone


import os
import json


class PublicDataLoader:
    def run(self, company_name: str, max_pages: int = 30) -> dict:
        website = find_company_website(company_name)

        flat_pages = crawl_website(website, max_pages=max_pages)

        hierarchical_pages = build_page_hierarchy(flat_pages)

        return {
            "company_name": company_name,
            "website": {
                "base_url": website,
                "discovered_via": "llm",
            },
            "pages": hierarchical_pages,
            "metadata": {
                "crawl_time": datetime.now(timezone.utc).isoformat(),
                "page_count": len(flat_pages),
            },
        }


if __name__ == "__main__":
    loader = PublicDataLoader()
    data = loader.run("automotive kalyani forge", max_pages=40)

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/public_data_bundle.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Public data bundle saved")
