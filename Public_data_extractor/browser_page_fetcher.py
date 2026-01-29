from playwright.sync_api import sync_playwright

# from text_normalizer import normalize_text
from urllib.parse import urlparse


def derive_title_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return ""

    parts = path.split("/")
    return " – ".join(p.replace("-", " ").title() for p in parts[-2:])


def fetch_with_browser(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30000)

        # 1️⃣ Try H1
        h1 = page.query_selector("h1")
        h1_text = h1.inner_text().strip() if h1 else ""

        # 2️⃣ Try breadcrumbs
        breadcrumb_nodes = page.query_selector_all(
            "nav a, .breadcrumb a, .breadcrumbs a"
        )
        breadcrumb_text = " > ".join(
            [b.inner_text().strip() for b in breadcrumb_nodes if b.inner_text()]
        )

        # 3️⃣ Fallback title
        fallback_title = page.title()

        # 4️⃣ URL-derived title
        url_title = derive_title_from_url(url)

        # Priority resolution
        title = h1_text or breadcrumb_text or url_title or fallback_title

        text = page.inner_text("body")

        browser.close()

    return {"url": url, "title": title, "text": text}
