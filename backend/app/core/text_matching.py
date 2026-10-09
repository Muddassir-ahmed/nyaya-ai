import re


def _normalize_text(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text.lower().strip(),
    )


def _matches_keyword(
    normalized_text: str,
    keyword: str,
) -> bool:
    normalized_keyword = _normalize_text(keyword)

    if not normalized_keyword:
        return False

    pattern = (
        rf"(?<!\w)"
        rf"{re.escape(normalized_keyword)}"
        rf"(?!\w)"
    )

    return re.search(
        pattern,
        normalized_text,
    ) is not None


def contains_any(
    text: str,
    keywords: set[str],
) -> bool:
    """
    Return True if any keyword or phrase matches using
    boundary-aware matching.

    Examples:
    - "fire" does not match "firewall"
    - "hack" does not match "hackathon"
    - "child" does not match "childhood"
    """

    normalized_text = _normalize_text(text)

    return any(
        _matches_keyword(
            normalized_text,
            keyword,
        )
        for keyword in keywords
    )


def count_matches(
    text: str,
    keywords: set[str],
) -> int:
    """
    Count how many distinct keywords or phrases match the text
    using boundary-aware matching.

    This is useful for deterministic category/domain scoring.
    """

    normalized_text = _normalize_text(text)

    return sum(
        1
        for keyword in keywords
        if _matches_keyword(
            normalized_text,
            keyword,
        )
    )