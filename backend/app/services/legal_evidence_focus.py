from __future__ import annotations

from collections import defaultdict
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_chunk import LegalChunk
from app.schemas.legal_query_plan import LegalQuestionAspect


WORD_PATTERN = re.compile(r"[A-Za-z0-9]+")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can",
    "does", "for", "from", "has", "have", "how", "in", "is",
    "it", "may", "of", "on", "or", "that", "the", "this", "to",
    "under", "was", "what", "which", "who", "with",
    # Corpus names and question scaffolding identify where/how to search,
    # not which provision controls.  Counting them allowed BNS Section 1
    # (the title/application provision) to beat substantive provisions.
    "act", "article", "bharatiya", "bns", "criminal", "describ",
    "india", "indian", "law", "legal", "nyaya", "offence",
    "offense", "penalty", "provision", "punishment", "rule",
    "sanhita", "section",
}

COMPARISON_PATTERN = re.compile(
    r"\b(compare|comparison|difference\s+between|versus|vs\.?)\b",
    re.IGNORECASE,
)
DEFINITION_PATTERN = re.compile(
    r"\b(define|defined|definition|meaning|what\s+is|"
    r"which\s+(?:bns\s+)?offen[cs]e\s+describes)\b",
    re.IGNORECASE,
)
PUNISHMENT_PATTERN = re.compile(
    r"\b(punish(?:ment|ed)?|penalt(?:y|ies)|sentence|sentencing)\b",
    re.IGNORECASE,
)
RIGHT_PATTERN = re.compile(
    r"\b(right|rights|constitutional\s+protection|fundamental\s+right)\b",
    re.IGNORECASE,
)

DEFINITION_CUES = (
    "means",
    "is said to",
    "shall be deemed",
    "is defined",
    "commits a terrorist act",
    "is snatching if",
)
PUNISHMENT_CUES = (
    "shall be punished",
    "punishable with",
    "imprisonment",
    "liable to fine",
    "death or imprisonment",
    "community service",
)


def _stem(word: str) -> str:
    normalized = word.casefold()

    if normalized.endswith("ly") and len(normalized) > 5:
        normalized = normalized[:-2]

    removed_suffix = False

    for suffix in ("ingly", "edly", "ing", "ed", "es", "s"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 3:
            normalized = normalized[: -len(suffix)]
            removed_suffix = True
            break

    if (
        removed_suffix
        and len(normalized) >= 4
        and normalized[-1] == normalized[-2]
    ):
        normalized = normalized[:-1]

    return normalized


def _tokens(text: str) -> set[str]:
    tokens = {_stem(word) for word in WORD_PATTERN.findall(text)}
    return {
        token
        for token in tokens
        if len(token) >= 3 and token not in STOPWORDS
    }


def _overlap_score(query: str, content: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(content)) / len(query_tokens)


def _section_key(
    chunk: LegalChunk,
) -> tuple[int, int | None, int] | None:
    if chunk.section_id is None:
        return None
    return (chunk.document_id, chunk.version_id, chunk.section_id)


def _unit_key(chunk: LegalChunk) -> tuple[str, int]:
    if chunk.subsection_id is not None:
        return ("subsection", chunk.subsection_id)
    return ("chunk", chunk.id)


def _requested_aspects(
    user_query: str,
    planned_aspects: list[LegalQuestionAspect],
) -> set[LegalQuestionAspect]:
    aspects = set(planned_aspects)
    if DEFINITION_PATTERN.search(user_query):
        aspects.add(LegalQuestionAspect.DEFINITION)
    if PUNISHMENT_PATTERN.search(user_query):
        aspects.add(LegalQuestionAspect.PUNISHMENT)
    if RIGHT_PATTERN.search(user_query):
        aspects.add(LegalQuestionAspect.RIGHT)
    return aspects


def _best_relevance(
    chunks: list[LegalChunk],
    queries: list[str],
) -> float:
    return max(
        (
            _overlap_score(query, chunk.content)
            for chunk in chunks
            for query in queries
        ),
        default=0.0,
    )


def _choose_section(
    *,
    chunks: list[LegalChunk],
    queries: list[str],
    aspects: set[LegalQuestionAspect],
) -> tuple[int, int | None, int] | None:
    groups: dict[tuple[int, int | None, int], list[LegalChunk]] = defaultdict(list)

    for chunk in chunks:
        key = _section_key(chunk)
        if key is not None:
            groups[key].append(chunk)

    if not groups:
        return None
    if len(groups) == 1:
        return next(iter(groups))

    cue_sets: list[tuple[str, ...]] = []
    if LegalQuestionAspect.DEFINITION in aspects:
        cue_sets.append(DEFINITION_CUES)
    if LegalQuestionAspect.PUNISHMENT in aspects:
        cue_sets.append(PUNISHMENT_CUES)

    def aspect_coverage(
        group_chunks: list[LegalChunk],
    ) -> int:
        text = _unit_text(group_chunks)
        return sum(
            _cue_count(text, cues) > 0
            for cues in cue_sets
        )

    positions = {
        key: min(
            index
            for index, chunk in enumerate(chunks)
            if _section_key(chunk) == key
        )
        for key in groups
    }

    ranked = sorted(
        (
            (
                aspect_coverage(group_chunks),
                _best_relevance(group_chunks, queries),
                -positions[key],
                key,
            )
            for key, group_chunks in groups.items()
        ),
        reverse=True,
    )
    best_coverage, best_score, _, best_key = ranked[0]

    comparable_scores = [
        score
        for coverage, score, _, _ in ranked[1:]
        if coverage == best_coverage
    ]
    second_score = (
        comparable_scores[0]
        if comparable_scores
        else 0.0
    )

    # Preserve broad retrieval when the text does not identify a clear
    # controlling provision.  Focusing must improve precision without
    # hiding alternative provisions for an ambiguous question.
    if best_score < 0.18:
        return None
    if not (
        second_score == 0.0
        or best_score >= second_score + 0.07
        or best_score >= second_score * 1.5
    ):
        return None
    return best_key


def _unit_text(chunks: list[LegalChunk]) -> str:
    return "\n".join(chunk.content for chunk in chunks)


def _cue_count(text: str, cues: tuple[str, ...]) -> int:
    normalized = " ".join(text.casefold().split())
    return sum(cue in normalized for cue in cues)


def _choose_unit_for_aspect(
    *,
    units: dict[tuple[str, int], list[LegalChunk]],
    queries: list[str],
    cues: tuple[str, ...],
) -> tuple[str, int]:
    return max(
        units,
        key=lambda unit_key: (
            _cue_count(_unit_text(units[unit_key]), cues) > 0,
            _best_relevance(units[unit_key], queries),
            _cue_count(_unit_text(units[unit_key]), cues),
            -min(chunk.id for chunk in units[unit_key]),
        ),
    )


def _focus_within_section(
    *,
    section_chunks: list[LegalChunk],
    queries: list[str],
    aspects: set[LegalQuestionAspect],
) -> list[LegalChunk]:
    units: dict[tuple[str, int], list[LegalChunk]] = defaultdict(list)
    for chunk in section_chunks:
        units[_unit_key(chunk)].append(chunk)

    if not units:
        return section_chunks

    selected: set[tuple[str, int]] = set()
    if LegalQuestionAspect.DEFINITION in aspects:
        selected.add(
            _choose_unit_for_aspect(
                units=units,
                queries=queries,
                cues=DEFINITION_CUES,
            )
        )
    if LegalQuestionAspect.PUNISHMENT in aspects:
        selected.add(
            _choose_unit_for_aspect(
                units=units,
                queries=queries,
                cues=PUNISHMENT_CUES,
            )
        )

    if not selected:
        selected.add(
            max(
                units,
                key=lambda unit_key: (
                    _best_relevance(units[unit_key], queries),
                    -min(chunk.id for chunk in units[unit_key]),
                ),
            )
        )

    return sorted(
        (
            chunk
            for chunk in section_chunks
            if _unit_key(chunk) in selected
        ),
        key=lambda chunk: chunk.id,
    )


async def focus_legal_chunks(
    *,
    db: AsyncSession | None,
    user_query: str,
    retrieval_queries: list[str],
    chunks: list[LegalChunk],
    requested_aspects: list[LegalQuestionAspect] | None = None,
) -> list[LegalChunk]:
    """Return complete requested units from a clear controlling section.

    Hybrid retrieval remains broad for recall.  This read-only stage
    reduces generation context only when one section is clearly related
    to the question.  Ambiguous and comparison questions retain the
    original candidate set.
    """

    if db is None or not chunks:
        return chunks

    aspects = _requested_aspects(user_query, requested_aspects or [])
    if (
        LegalQuestionAspect.COMPARISON in aspects
        or COMPARISON_PATTERN.search(user_query)
    ):
        return chunks

    queries = [user_query, *retrieval_queries]
    section_key = _choose_section(
        chunks=chunks,
        queries=queries,
        aspects=aspects,
    )
    if section_key is None:
        return chunks

    document_id, version_id, section_id = section_key
    result = await db.execute(
        select(LegalChunk)
        .where(
            LegalChunk.document_id == document_id,
            LegalChunk.version_id == version_id,
            LegalChunk.section_id == section_id,
        )
        .order_by(LegalChunk.id)
    )
    section_chunks = list(result.scalars().all())
    if not section_chunks:
        return chunks

    return _focus_within_section(
        section_chunks=section_chunks,
        queries=queries,
        aspects=aspects,
    )
