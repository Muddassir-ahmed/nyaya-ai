import re

from app.schemas.citation_validation import (
    CitationValidationResult,
)
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence


class GeneratedAnswerCitationValidator:

    @staticmethod
    def _normalize_citation_id(
        citation: str,
    ) -> str | None:
        """
        Normalize strictly formatted evidence IDs.

        Accepted:
            E1
            e1
            [E1]
            [ e1 ]

        Rejected:
            Article 21
            Constitution E1
            E1 extra text
            E999 unless E999 actually exists
        """

        match = re.fullmatch(
            r"\[\s*(E\d+)\s*\]|(E\d+)",
            citation.strip(),
            flags=re.IGNORECASE,
        )

        if match is None:
            return None

        return (
            match.group(1)
            or match.group(2)
        ).upper()

    @staticmethod
    def validate(
        answer: LegalAnswer,
        evidence: list[LegalEvidence],
    ) -> CitationValidationResult:

        if not evidence:
            return CitationValidationResult(
                is_valid=False,
                citation_completeness=0.0,
                validation_reasons=[
                    "No verified legal evidence was available."
                ],
            )

        valid_ids = {
            item.citation_id
            for item in evidence
            if item.citation_id
        }

        valid_citations = []
        invalid_citations = []

        for citation in answer.citations:

            citation_id = (
                GeneratedAnswerCitationValidator
                ._normalize_citation_id(
                    citation
                )
            )

            if (
                citation_id is not None
                and citation_id in valid_ids
            ):
                valid_citations.append(
                    citation_id
                )
            else:
                invalid_citations.append(
                    citation
                )

        citation_count = len(answer.citations)

        completeness = (
            len(valid_citations) / citation_count
            if citation_count > 0
            else 0.0
        )

        reasons = []

        if invalid_citations:
            reasons.append(
                "One or more generated citation IDs "
                "do not match verified legal evidence."
            )

        if not answer.citations:
            reasons.append(
                "The generated answer contains no citations."
            )

        if not reasons:
            reasons.append(
                "All generated citation IDs match verified evidence."
            )

        is_valid = (
            len(invalid_citations) == 0
            and len(answer.citations) > 0
        )

        return CitationValidationResult(
            is_valid=is_valid,
            citation_completeness=completeness,
            valid_citations=valid_citations,
            invalid_citations=invalid_citations,
            unsupported_claims=[],
            validation_reasons=reasons,
        )