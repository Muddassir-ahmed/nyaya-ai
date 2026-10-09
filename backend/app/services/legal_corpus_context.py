from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.act import Act
from app.models.legal_version import LegalVersion


BNS_ACT_NAME = "Bharatiya Nyaya Sanhita, 2023"
BNS_SHORT_NAME = "BNS"


BNS_REFERENCE_PATTERN = re.compile(
    r"\b(?:bns|bharatiya\s+nyaya\s+sanhita)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LegalCorpusContext:
    act_id: int
    version_id: int
    legal_jurisdiction: str


def has_explicit_bns_reference(
    query: str,
) -> bool:
    return BNS_REFERENCE_PATTERN.search(query) is not None


async def get_bns_context(
    db: AsyncSession,
) -> LegalCorpusContext:
    """
    Resolve the single active, verified BNS corpus identity.

    IDs are resolved from structured metadata and are never hardcoded.
    This function is read-only.
    """

    act_result = await db.execute(
        select(Act).where(
            Act.name == BNS_ACT_NAME,
            Act.short_name == BNS_SHORT_NAME,
            Act.status == "active",
        )
    )

    acts = act_result.scalars().all()

    if len(acts) != 1:
        raise RuntimeError(
            "Expected exactly one active BNS Act, found "
            f"{len(acts)}."
        )

    act = acts[0]

    version_result = await db.execute(
        select(LegalVersion).where(
            LegalVersion.act_id == act.id,
            LegalVersion.status == "active",
        )
    )

    versions = version_result.scalars().all()

    if len(versions) != 1:
        raise RuntimeError(
            "Expected exactly one active BNS version, found "
            f"{len(versions)}."
        )

    return LegalCorpusContext(
        act_id=act.id,
        version_id=versions[0].id,
        legal_jurisdiction="IN",
    )
