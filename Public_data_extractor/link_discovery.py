import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from browser_link_discovery import discover_links_with_browser

HEADERS = {"User-Agent": "Mozilla/5.0"}


def discover_links(base_url: str, max_urls=30) -> set[str]:
    domain = urlparse(base_url).netloc
    urls = set()

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            parsed = urlparse(href)
            if parsed.netloc == domain:
                urls.add(parsed.scheme + "://" + parsed.netloc + parsed.path)

        if len(urls) >= 5:
            return set(list(urls)[:max_urls])

    except Exception:
        pass

    # Fallback: browser-based discovery
    return discover_links_with_browser(base_url, max_urls)
