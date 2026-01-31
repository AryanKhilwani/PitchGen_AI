from playwright.sync_api import sync_playwright
from text_normalizer import normalize_text


class BrowserFetcher:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

    def fetch(self, url: str) -> dict:
        page = self.browser.new_page()
        page.goto(url, timeout=30000, wait_until="networkidle")

        # ----- TITLE LOGIC (unchanged, just safer) -----
        h1 = page.query_selector("h1")
        title = h1.inner_text().strip() if h1 else page.title()

        # ----- SEGMENTED CONTENT EXTRACTION -----
        def safe_inner_text(selector: str) -> str:
            try:
                el = page.query_selector(selector)
                return normalize_text(el.inner_text()) if el else ""
            except Exception:
                return ""

        main_text = safe_inner_text("main")
        nav_text = safe_inner_text("nav")
        footer_text = safe_inner_text("footer")

        # Fallback: entire page body
        full_text = normalize_text(page.inner_text("body"))

        page.close()

        return {
            "url": url,
            "title": title,
            "content_blocks": {
                "main": main_text,
                "nav": nav_text,
                "footer": footer_text,
                "full": full_text,
            },
            "method": "browser",
        }

    def close(self):
        self.browser.close()
        self.playwright.stop()
