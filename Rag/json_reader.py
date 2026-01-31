def iter_indexable_pages(json_data: dict):
    """
    Yields one page at a time.
    """
    pages = json_data.get("pages", {})

    for _, page in pages.items():
        content = page.get("content_blocks", {}).get("main", "")
        title = page.get("title", "")
        url = page.get("url", "")

        if content and len(content) >= 300:
            yield {"url": url, "title": title, "text": content}
