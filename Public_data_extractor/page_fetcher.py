import requests
from bs4 import BeautifulSoup
from waf_detector import is_waf_block
from browser_page_fetcher import fetch_with_browser

# from text_normalizer import normalize_text

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}


def fetch_page(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text("\n")

        if is_waf_block(text):
            raise RuntimeError("WAF detected")

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "text": text,
            "method": "static",
        }

    except Exception:
        browser_data = fetch_with_browser(url)
        browser_data["method"] = "browser"
        return browser_data
