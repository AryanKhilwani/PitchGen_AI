from url_hierarchy import get_parent_path, get_path


def build_page_hierarchy(flat_pages: dict) -> dict:
    """
    flat_pages: {url: page_data}
    returns: hierarchical tree
    """

    tree = {}

    # First pass: create nodes
    nodes = {}
    for url, data in flat_pages.items():
        path = get_path(url)
        nodes[path] = {
            "url": url,
            "title": data.get("title", ""),
            "text": data.get("text", ""),
            "children": {},
        }

    # Second pass: attach children to parents
    for path, node in nodes.items():
        parent_path = get_parent_path(node["url"])

        if parent_path and parent_path in nodes:
            nodes[parent_path]["children"][path] = node
        else:
            tree[path] = node

    return tree
