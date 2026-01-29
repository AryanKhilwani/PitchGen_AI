from website_discovery import find_company_website
from website_crawler import crawl_website
from datetime import datetime
import os
import json


class PublicDataLoader:
    def run(self, company_name: str, max_pages: int = 20) -> dict:
        website = find_company_website(company_name)

        # Crawl entire website (not just homepage)
        pages = crawl_website(website, max_pages=max_pages)

        return {
            "company_name": company_name,
            "website": {
                "base_url": website,
                "discovered_via": "llm",
            },
            "pages": pages,
            "metadata": {
                "crawl_time": datetime.utcnow().isoformat(),
                "page_count": len(pages),
            },
        }


if __name__ == "__main__":
    loader = PublicDataLoader()
    data = loader.run("automotive kalyani forge", max_pages=40)

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/public_data_bundle.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Public data bundle saved")
