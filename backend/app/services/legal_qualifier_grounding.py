"""Deterministic grounding for material legal-condition polarity.

This module intentionally handles only reviewed, high-confidence qualifier
contradictions. It is not a general natural-language inference system.
"""

import re

from app.schemas.legal_evidence import LegalEvidence


PROVOCATION_CONDITION_MISMATCH_REASON = (
    "The claimed provision's provocation condition contradicts the "
    "provocation condition stated in the cited evidence."
)


_SECTION_REFERENCE_PATTERN = re.compile(
    r"\bsection\s+(?P<section>\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)\b",
    flags=re.IGNORECASE,
)

_NEGATIVE_PROVOCATION_PATTERNS = (
    re.compile(
        r"\bwithout\s+(?:any\s+)?(?:grave\s+and\s+sudden\s+)?provocation\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bno\s+(?:grave\s+and\s+sudden\s+)?provocation\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\botherwise\s+than\s+(?:on\s+)?"
        r"(?:grave\s+and\s+sudden\s+)?provocation\b",
        flags=re.IGNORECASE,
    ),
)

_POSITIVE_PROVOCATION_PATTERNS = (
    re.compile(
        r"\bon\s+(?:grave\s+and\s+sudden\s+)?provocation\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bdue\s+to\s+(?:grave\s+and\s+sudden\s+)?provocation\b",
        flags=re.IGNORECASE,
    ),
)

_NEGATED_APPLICATION_PATTERN = re.compile(
    r"\b(?:does|do|did|may|might|would|should|is|are|was|were)\s+not\s+apply\b"
    r"|\bnot\s+applicable\b",
    flags=re.IGNORECASE,
)


def _normalize_section(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[\s()]+", "", str(value)).lower()
    return normalized or None


def _scoped_evidence(
    statement: str,
    evidence: list[LegalEvidence],
) -> list[LegalEvidence]:
    referenced_sections = {
        _normalize_section(match.group("section"))
        for match in _SECTION_REFERENCE_PATTERN.finditer(statement)
    }
    referenced_sections.discard(None)

    if not referenced_sections:
        return evidence

    matched = [
        item
        for item in evidence
        if _normalize_section(item.section_number) in referenced_sections
    ]

    # Explicit-reference validation is handled separately. If structured
    # metadata is unavailable here, retain the caller's evidence set.
    return matched or evidence


def _provocation_polarity(text: str) -> set[str]:
    if "provocation" not in text.lower():
        return set()

    negative_spans: list[tuple[int, int]] = []
    polarity: set[str] = set()

    for pattern in _NEGATIVE_PROVOCATION_PATTERNS:
        for match in pattern.finditer(text):
            negative_spans.append(match.span())
            polarity.add("negative")

    # Mask negative phrases so their embedded "on ... provocation" text is
    # not also classified as affirmative.
    positive_text = list(text)
    for start, end in negative_spans:
        positive_text[start:end] = " " * (end - start)
    unmasked = "".join(positive_text)

    if any(pattern.search(unmasked) for pattern in _POSITIVE_PROVOCATION_PATTERNS):
        polarity.add("positive")

    return polarity


def provocation_condition_mismatch(
    statement: str,
    evidence: list[LegalEvidence],
    *,
    user_query: str | None = None,
) -> LegalEvidence | None:
    """Return contradictory evidence for an unambiguous polarity mismatch."""

    if _NEGATED_APPLICATION_PATTERN.search(statement):
        return None

    statement_polarity = _provocation_polarity(statement)

    # A short legal-basis field may name only a Section. In that narrow case,
    # use the user's explicit factual qualifier as the applicability context.
    if not statement_polarity and _SECTION_REFERENCE_PATTERN.search(statement):
        statement_polarity = _provocation_polarity(user_query or "")

    # Mixed/explanatory statements require semantic interpretation and must
    # not be rejected by this deterministic rule.
    if len(statement_polarity) != 1:
        return None

    scoped = _scoped_evidence(statement, evidence)
    evidence_by_polarity: dict[str, list[LegalEvidence]] = {
        "positive": [],
        "negative": [],
    }

    for item in scoped:
        for polarity in _provocation_polarity(item.content):
            evidence_by_polarity[polarity].append(item)

    expected = next(iter(statement_polarity))
    opposite = "positive" if expected == "negative" else "negative"

    # Reject only when the scoped evidence supports the opposite condition
    # and contains no same-polarity support.
    if evidence_by_polarity[opposite] and not evidence_by_polarity[expected]:
        return evidence_by_polarity[opposite][0]

    return None
