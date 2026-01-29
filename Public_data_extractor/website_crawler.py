from urllib.parse import urlparse
from link_discovery import discover_links
from page_fetcher import fetch_page


def crawl_website(base_url: str, max_pages: int = 25) -> dict:
    """
    Crawl an entire website starting from base_url.

    Returns:
        pages: {
            url: {
                url,
                title,
                text,
                method
            }
        }
    """

    # Step 1: discover internal URLs
    discovered_urls = discover_links(base_url, max_urls=max_pages)

    pages = {}
    for url in discovered_urls:
        try:
            page_data = fetch_page(url)

            # Drop empty / useless pages early
            if not page_data.get("text") or len(page_data["text"]) < 300:
                continue

            pages[url] = page_data

        except Exception:
            # Fail silently per page — crawler must be robust
            continue

    return pages
