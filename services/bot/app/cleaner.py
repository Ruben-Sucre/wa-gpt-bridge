import re


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Normalize whitespace
    s = re.sub(r"\s+", " ", text).strip()
    # Remove control characters
    s = re.sub(r"[\x00-\x1F\x7F]+", "", s)
    return s
