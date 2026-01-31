from playwright.async_api import async_playwright
from text_normalizer import normalize_text


async def fetch_page(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")

            title = await page.title()
            text = await page.inner_text("body")

            return {
                "url": url,
                "title": title,
                "text": normalize_text(text),
                "method": "browser",
            }

        except Exception:
            return {}

        finally:
            await browser.close()
