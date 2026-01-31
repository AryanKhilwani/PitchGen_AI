from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse


async def discover_links_with_browser(base_url: str, max_urls: int = 50) -> set[str]:
    discovered = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(base_url, timeout=60000)
        await page.wait_for_load_state("networkidle")

        anchors = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))"
        )

        for href in anchors:
            if not href:
                continue

            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            if parsed.netloc != urlparse(base_url).netloc:
                continue

            discovered.add(full_url)

            if len(discovered) >= max_urls:
                break

        await browser.close()

    return discovered
