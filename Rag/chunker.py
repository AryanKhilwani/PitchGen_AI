def chunk_text(text: str, max_chars: int):
    start = 0
    length = len(text)

    while start < length:
        yield text[start : start + max_chars]
        start += max_chars
