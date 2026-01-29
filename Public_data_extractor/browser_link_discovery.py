from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urljoin


def discover_links_with_browser(base_url: str, max_urls=30) -> set[str]:
    urls = set()
    domain = urlparse(base_url).netloc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url, timeout=30000)

        anchors = page.query_selector_all("a[href]")
        for a in anchors:
            href = a.get_attribute("href")
            if not href:
                continue

            full = urljoin(base_url, href)
            parsed = urlparse(full)

            if parsed.netloc == domain:
                urls.add(parsed.scheme + "://" + parsed.netloc + parsed.path)

            if len(urls) >= max_urls:
                break

        browser.close()

    return urls
