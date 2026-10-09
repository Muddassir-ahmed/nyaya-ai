from enum import Enum

from pydantic import BaseModel, Field


class LegalCorpusHint(str, Enum):
    BNS = "bns"
    CONSTITUTION = "constitution"
    BOTH = "both"
    UNSPECIFIED = "unspecified"


class LegalQuestionAspect(str, Enum):
    DEFINITION = "definition"
    APPLICABILITY = "applicability"
    PUNISHMENT = "punishment"
    EXCEPTION = "exception"
    COMPARISON = "comparison"
    RIGHT = "right"
    REMEDY = "remedy"
    OTHER = "other"


class LegalQueryPlan(BaseModel):
    """
    Retrieval-only interpretation of a user's question.

    The plan is never legal evidence and must never be shown as a
    legal answer.  Its search phrases are hypotheses used to locate
    verified source text.
    """

    search_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    corpus_hint: LegalCorpusHint = (
        LegalCorpusHint.UNSPECIFIED
    )

    requested_aspects: list[LegalQuestionAspect] = Field(
        default_factory=list,
        max_length=6,
    )

    ambiguity_notes: list[str] = Field(
        default_factory=list,
        max_length=4,
    )
