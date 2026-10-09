from app.schemas.legal_evidence import LegalEvidence
from app.services.verified_evidence import (
    verify_evidence_list,
)


def make_valid_evidence(
    chunk_id: int,
) -> LegalEvidence:

    return LegalEvidence(
        chunk_id=chunk_id,
        content="Legal provision text.",

        act_name=(
            "Bharatiya Nyaya Sanhita, 2023"
        ),

        act_short_name="BNS",

        version_label=(
            "BNS 2023 — Original"
        ),

        section_number="303",

        section_title="Theft",

        source_name=(
            "Bharatiya Nyaya Sanhita, 2023 — Gazette"
        ),

        source_publisher=(
            "Ministry of Home Affairs, "
            "Government of India"
        ),

        source_url=(
            "https://www.mha.gov.in/"
        ),

        is_verified=True,
    )


def test_only_verified_evidence_is_returned():

    valid = make_valid_evidence(1)

    invalid = make_valid_evidence(2)
    invalid.is_verified = False

    result = verify_evidence_list(
        [valid, invalid]
    )

    assert len(result) == 1

    assert result[0].evidence.chunk_id == 1

    assert (
        result[0].verification.is_valid
        is True
    )


def test_all_valid_evidence_is_preserved():

    evidence = [
        make_valid_evidence(1),
        make_valid_evidence(2),
        make_valid_evidence(3),
    ]

    result = verify_evidence_list(
        evidence
    )

    assert len(result) == 3

    assert [
        item.evidence.chunk_id
        for item in result
    ] == [1, 2, 3]


def test_all_invalid_evidence_returns_empty_list():

    evidence = [
        make_valid_evidence(1),
        make_valid_evidence(2),
    ]

    for item in evidence:
        item.is_verified = False

    result = verify_evidence_list(
        evidence
    )

    assert result == []