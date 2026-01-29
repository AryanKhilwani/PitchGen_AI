import requests
from urllib.parse import urlparse
from url_utils import normalize_url

BLOCKLIST_DOMAINS = {
    "wikipedia.org",
    "linkedin.com",
    "crunchbase.com",
    "bloomberg.com",
    "twitter.com",
    "facebook.com",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def validate_and_canonicalize(raw_url: str) -> str:
    url = normalize_url(raw_url)

    try:
        r = requests.get(url, timeout=15, allow_redirects=True, headers=HEADERS)
    except Exception as e:
        raise ValueError(f"Website not reachable: {e}")

    final_url = r.url.rstrip("/")
    domain = urlparse(final_url).netloc.lower()

    # Reject known bad sources
    if any(bad in domain for bad in BLOCKLIST_DOMAINS):
        raise ValueError(f"Blocked domain: {domain}")

    # Reject only truly invalid cases
    if r.status_code in {404, 410}:
        raise ValueError(f"Website not found: {r.status_code}")

    return final_url
