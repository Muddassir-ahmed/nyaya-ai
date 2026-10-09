import re

from app.schemas.citation import CitationVerification
from app.schemas.legal_evidence import LegalEvidence


CONSTITUTION_SCHEDULE_PATTERN = re.compile(
    r"^(First|Second|Third|Fourth|Fifth|Sixth|"
    r"Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth)"
    r"\s+Schedule$",
    flags=re.IGNORECASE,
)


def _get_constitution_document_level_kind(
    evidence: LegalEvidence,
) -> str | None:
    """
    Recognize Constitution chunks that are intentionally
    document-level rather than Article/Section-level.

    Allowed in V1:
    - Preamble
    - First through Twelfth Schedule

    Other chunks without section metadata remain invalid.
    """

    if (
        evidence.act_name
        != "The Constitution of India"
    ):
        return None

    if (
        evidence.document_title
        != "The Constitution of India"
    ):
        return None

    if evidence.document_type != "constitution":
        return None

    # If a section exists, this is normal
    # Article/Section-level evidence.
    if evidence.section_number:
        return None

    lines = [
        line.strip()
        for line in evidence.content.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        return None

    heading = lines[1]

    if heading.lower() == "preamble":
        return "Preamble"

    if CONSTITUTION_SCHEDULE_PATTERN.fullmatch(
        heading
    ):
        return heading

    return None


def verify_legal_evidence(
    evidence: LegalEvidence,
) -> CitationVerification:

    has_source = bool(
        evidence.source_name
        and evidence.source_publisher
    )

    has_source_url = bool(
        evidence.source_url
    )

    has_act = bool(
        evidence.act_name
    )

    has_version = bool(
        evidence.version_label
    )

    has_section = bool(
        evidence.section_number
    )

    document_level_kind = (
        _get_constitution_document_level_kind(
            evidence
        )
    )

    # Normal legal evidence requires a Section/Article.
    #
    # Constitution Preamble and Schedules are legitimate
    # document-level evidence and therefore do not have
    # section_number values.
    has_valid_legal_hierarchy = (
        has_section
        or document_level_kind is not None
    )

    document_verified = (
        evidence.is_verified
    )

    checks = [
        has_source,
        has_source_url,
        has_act,
        has_version,
        has_valid_legal_hierarchy,
        document_verified,
    ]

    is_valid = all(checks)

    if is_valid:
        reason = (
            "Evidence has a verified document, "
            "legal hierarchy, and source information."
        )

    else:
        failed_checks = []

        if not has_source:
            failed_checks.append(
                "source information"
            )

        if not has_source_url:
            failed_checks.append(
                "source URL"
            )

        if not has_act:
            failed_checks.append(
                "act"
            )

        if not has_version:
            failed_checks.append(
                "legal version"
            )

        if not has_valid_legal_hierarchy:
            failed_checks.append(
                "legal hierarchy"
            )

        if not document_verified:
            failed_checks.append(
                "verified document"
            )

        reason = (
            "Evidence failed verification because "
            "the following information is missing or "
            "unverified: "
            + ", ".join(failed_checks)
            + "."
        )

    citation_text = None

    if is_valid:

        citation_text = (
            f"{evidence.act_name}"
        )

        if evidence.act_short_name:
            citation_text += (
                f" ({evidence.act_short_name})"
            )

        if evidence.section_number:
            citation_text += (
                f", Section "
                f"{evidence.section_number}"
            )

        elif document_level_kind:
            citation_text += (
                f", {document_level_kind}"
            )

        if evidence.section_title:
            citation_text += (
                f" — "
                f"{evidence.section_title}"
            )

        if evidence.source_name:
            citation_text += (
                f". Source: "
                f"{evidence.source_name}"
            )

    return CitationVerification(
        chunk_id=evidence.chunk_id,
        is_valid=is_valid,
        has_source=has_source,
        has_source_url=has_source_url,
        has_act=has_act,
        has_version=has_version,
        has_section=has_section,
        document_verified=document_verified,
        citation_text=citation_text,
        verification_reason=reason,
    )