def is_hash(text: str) -> bool:
    return len(text) == 64 and all(c in '0123456789abcdef' for c in text)
