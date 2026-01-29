from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url

    return url
