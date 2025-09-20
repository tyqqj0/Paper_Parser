from typing import Optional


def normalize_title_norm(title: str) -> Optional[str]:
    """Normalize a title for strong matching.

    Rules:
    - lower-case
    - collapse whitespace to single space
    - strip Unicode punctuation and symbols
    - trim
    Returns None if the result is empty.
    """
    try:
        import re
        t = str(title).lower()
        # replace tabs with space to match Cypher inline used before
        t = t.replace("\t", " ")
        t = re.sub(r"\s+", " ", t)
        # remove punctuation and symbols (Unicode classes P and S)
        t = re.sub(r"[\p{P}\p{S}]", "", t)
        t = t.strip()
        return t if t else None
    except Exception:
        try:
            t = str(title).strip().lower()
            return t or None
        except Exception:
            return None


