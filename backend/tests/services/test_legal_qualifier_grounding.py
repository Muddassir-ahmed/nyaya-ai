"""C18 regressions for the observed unprovoked-assault false positive."""

from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.answer_integrity import LegalAnswerIntegrityValidator
from app.services.claim_validator import LegalClaimValidator
from app.services.legal_qualifier_grounding import (
    PROVOCATION_CONDITION_MISMATCH_REASON,
)


QUERY = (
    "A person intentionally hit me without any provocation. I am safe now. "
    "Which provisions of the Bharatiya Nyaya Sanhita may apply?"
)


def provoked_hurt() -> LegalEvidence:
    return LegalEvidence(
        citation_id="E1",
        chunk_id=4088,
        section_number="122",
        subsection_number="(1)",
        content=(
            "Whoever voluntarily causes hurt on grave and sudden "
            "provocation shall be punished with imprisonment of either "
            "description for a term which may extend to one month, or "
            "with fine which may extend to five thousand rupees, or with both."
        ),
    )


def unprovoked_force() -> LegalEvidence:
    return LegalEvidence(
        citation_id="E5",
        chunk_id=4112,
        section_number="131",
        content=(
            "Whoever assaults or uses criminal force to any person otherwise "
            "than on grave and sudden provocation given by that person, shall "
            "be punished with imprisonment of either description for a term "
            "which may extend to three months, or with fine which may extend "
            "to one thousand rupees, or with both."
        ),
    )


def observed_wrong_answer(citations: list[str] | None = None) -> LegalAnswer:
    return LegalAnswer(
        summary=(
            "Section 122 of the Bharatiya Nyaya Sanhita, 2023, applies to "
            "the case where a person intentionally hits another person "
            "without any provocation. The punishment for this offence is "
            "imprisonment of either description for a term which may extend "
            "to one month, or with fine which may extend to five thousand "
            "rupees, or with both."
        ),
        legal_basis=[
            "Section 122 of the Bharatiya Nyaya Sanhita, 2023"
        ],
        citations=citations or ["E1"],
    )


def test_observed_section_122_answer_fails_claim_grounding():
    result = LegalClaimValidator.validate(
        answer=observed_wrong_answer(),
        evidence=[provoked_hurt(), unprovoked_force()],
        user_query=QUERY,
    )

    assert result.is_valid is False
    assert result.claims[0].reason == PROVOCATION_CONDITION_MISMATCH_REASON


def test_explicit_section_scopes_qualifier_check_with_broad_citations():
    result = LegalClaimValidator.validate(
        answer=observed_wrong_answer(citations=["E1", "E5"]),
        evidence=[provoked_hurt(), unprovoked_force()],
        user_query=QUERY,
    )

    assert result.is_valid is False
    assert result.claims[0].reason == PROVOCATION_CONDITION_MISMATCH_REASON


def test_observed_section_122_answer_fails_answer_integrity():
    result = LegalAnswerIntegrityValidator.validate(
        user_query=QUERY,
        answer=observed_wrong_answer(),
        evidence=[provoked_hurt(), unprovoked_force()],
    )

    assert result.is_valid is False
    assert "contradictory_legal_qualifier" in {
        issue.code for issue in result.issues
    }


def test_matching_section_131_answer_passes_both_safety_gates():
    answer = LegalAnswer(
        summary=(
            "Section 131 applies to assault or use of criminal force "
            "otherwise than on grave and sudden provocation. It provides "
            "imprisonment of either description for a term which may extend "
            "to three months, or fine which may extend to one thousand "
            "rupees, or both."
        ),
        legal_basis=[
            (
                "Section 131 applies where assault or criminal force is used "
                "otherwise than on grave and sudden provocation."
            )
        ],
        citations=["E5"],
    )
    evidence = [provoked_hurt(), unprovoked_force()]

    claims = LegalClaimValidator.validate(
        answer=answer,
        evidence=evidence,
        user_query=QUERY,
    )
    integrity = LegalAnswerIntegrityValidator.validate(
        user_query=QUERY,
        answer=answer,
        evidence=evidence,
    )

    assert claims.is_valid is True
    assert integrity.is_valid is True


def test_explanation_of_non_applicability_is_not_a_false_positive():
    answer = LegalAnswer(
        summary=(
            "Section 122 applies on grave and sudden provocation; it may not "
            "apply where there was no provocation."
        ),
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[provoked_hurt()],
        user_query=QUERY,
    )

    assert result.claims[0].reason != PROVOCATION_CONDITION_MISMATCH_REASON
