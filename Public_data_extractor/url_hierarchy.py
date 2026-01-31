from urllib.parse import urlparse


def get_parent_path(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    if not path or path == "":
        return None

    parts = path.split("/")
    if len(parts) <= 2:
        return "/"

    parent = "/".join(parts[:-1])
    return parent + "/"


def get_path(url: str) -> str:
    path = urlparse(url).path
    return path if path.endswith("/") else path + "/"
