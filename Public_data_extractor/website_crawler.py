import asyncio
from browser_link_discovery import discover_links_with_browser
from page_fetcher import fetch_page


async def async_crawl_website(base_url: str, max_pages: int = 30) -> dict:
    urls = await discover_links_with_browser(base_url, max_urls=max_pages)

    semaphore = asyncio.Semaphore(5)

    async def fetch_with_limit(url):
        async with semaphore:
            return await fetch_page(url)

    tasks = [fetch_with_limit(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    pages = {}
    for result in results:
        if isinstance(result, dict) and "url" in result:
            pages[result["url"]] = result

    return pages


def crawl_website(base_url: str, max_pages: int = 30) -> dict:
    return asyncio.run(async_crawl_website(base_url, max_pages))
