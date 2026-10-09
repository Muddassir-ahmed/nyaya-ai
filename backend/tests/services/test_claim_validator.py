from app.schemas.claim_validation import ClaimSupportLevel
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.claim_validator import LegalClaimValidator


def make_evidence() -> LegalEvidence:
    return LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "Whoever takes movable property dishonestly out of the "
            "possession of any person without that person's consent "
            "commits theft."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        section_title="Theft",
        source_name="Bharatiya Nyaya Sanhita, 2023 — Gazette",
        source_publisher="Ministry of Home Affairs, Government of India",
        source_url="https://www.mha.gov.in/",
        is_verified=True,
    )


def test_supported_claim():
    answer = LegalAnswer(
        summary="Taking movable property dishonestly without consent can constitute theft.",
        legal_basis=[
            "Taking movable property dishonestly without consent can constitute theft."
        ],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[make_evidence()],
    )

    assert result.is_valid is True
    assert len(result.unsupported_claims) == 0
    assert result.claims[0].support_level == ClaimSupportLevel.SUPPORTED


def test_unsupported_claim():
    answer = LegalAnswer(
        summary="The punishment for theft is imprisonment for three years.",
        legal_basis=[
            "The punishment for theft is imprisonment for three years."
        ],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[make_evidence()],
    )

    assert result.is_valid is False
    assert len(result.unsupported_claims) > 0
    assert result.claims[0].support_level == ClaimSupportLevel.UNSUPPORTED


def test_claim_without_citation_is_unsupported():
    answer = LegalAnswer(
        summary="Taking movable property without consent can constitute theft.",
        legal_basis=[
            "Taking movable property without consent can constitute theft."
        ],
        citations=[],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[make_evidence()],
    )

    assert result.is_valid is False
    assert len(result.unsupported_claims) > 0
    assert result.claims[0].support_level == ClaimSupportLevel.UNSUPPORTED

def test_unsupported_summary_is_rejected():
    answer = LegalAnswer(
        summary=(
            "Every theft offence automatically results "
            "in ten years of imprisonment."
        ),
        legal_basis=[],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[make_evidence()],
    )

    assert result.is_valid is False

    assert (
        answer.summary
        in result.unsupported_claims
    )

def test_explicit_absence_contradiction_is_rejected():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=3027,
        content=(
            "The Constitution of India\n"
            "Preamble\n\n"
            "WE, THE PEOPLE OF INDIA, having solemnly "
            "resolved to constitute India into a "
            "SOVEREIGN SOCIALIST SECULAR DEMOCRATIC "
            "REPUBLIC."
        ),
    )

    answer = LegalAnswer(
        summary=(
            "Secularism is not explicitly mentioned "
            "in the Preamble."
        ),
        legal_basis=[],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is False

    assert (
        answer.summary
        in result.unsupported_claims
    )

    assert result.claims[0].support_level == (
        ClaimSupportLevel.UNSUPPORTED
    )

    assert "absent" in (
        result.claims[0].reason.lower()
    )

def test_negated_affirmative_claim_is_rejected():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "Article 25 guarantees freedom of "
            "conscience and freedom of religion."
        ),
    )

    answer = LegalAnswer(
        summary=(
            "Article 25 does not guarantee freedom "
            "of conscience and freedom of religion."
        ),
        legal_basis=[],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is False

    assert (
        answer.summary
        in result.unsupported_claims
    )

def test_affirmative_supported_claim_still_passes():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "Article 25 guarantees freedom of "
            "conscience and freedom of religion."
        ),
    )

    answer = LegalAnswer(
        summary=(
            "Article 25 guarantees freedom of "
            "conscience and freedom of religion."
        ),
        legal_basis=[],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is True

def test_preamble_morphological_paraphrase_is_grounded():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=3027,
        content=(
            "The Constitution of India\n"
            "Preamble\n\n"
            "WE, THE PEOPLE OF INDIA, having solemnly "
            "resolved to constitute India into a "
            "SOVEREIGN SOCIALIST SECULAR DEMOCRATIC "
            "REPUBLIC."
        ),
    )

    answer = LegalAnswer(
        summary=(
            "Secularism is mentioned as a component "
            "of the Republic, along with Socialism "
            "and Democracy."
        ),
        legal_basis=[],
        possible_options=[],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is True

    assert (
        answer.summary
        not in result.unsupported_claims
    )

def test_claim_grounding_accepts_verified_section_metadata():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "Whoever commits theft shall be punished "
            "according to this provision."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        subsection_number="(2)",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )

    answer = LegalAnswer(
        summary=(
            "Whoever commits theft shall be punished "
            "according to this provision."
        ),
        legal_basis=[
            (
                "Section 303(2) of the "
                "Bharatiya Nyaya Sanhita, 2023"
            )
        ],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is True
    assert result.unsupported_claims == []


def test_claim_grounding_still_rejects_unrelated_section_metadata():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "Whoever commits theft shall be punished "
            "according to this provision."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        subsection_number="(2)",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )

    answer = LegalAnswer(
        summary=(
            "Whoever commits theft shall be punished "
            "according to this provision."
        ),
        legal_basis=[
            (
                "Section 999 of the Completely "
                "Unrelated Act"
            )
        ],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is False

    assert result.unsupported_claims == [
        (
            "Section 999 of the Completely "
            "Unrelated Act"
        )
    ]

def test_wrong_section_reference_with_same_act_is_rejected():
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "Whoever commits theft shall be punished "
            "according to this provision."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        section_title="Theft",
        subsection_number="(2)",
        source_name="BNS Gazette",
        source_publisher="Ministry of Home Affairs",
        source_url="https://example.com",
        is_verified=True,
    )

    answer = LegalAnswer(
        summary=(
            "Whoever commits theft shall be punished "
            "according to this provision."
        ),
        legal_basis=[
            (
                "Section 999(2) of the "
                "Bharatiya Nyaya Sanhita, 2023"
            )
        ],
        citations=["E1"],
    )

    result = LegalClaimValidator.validate(
        answer=answer,
        evidence=[evidence],
    )

    assert result.is_valid is False

    assert any(
        "Section 999(2)"
        in claim
        for claim in result.unsupported_claims
    )

def test_evidence_marker_is_not_a_subsection():
    from app.services.claim_validator import SECTION_REFERENCE_PATTERN

    for text in ("Section 303 (E1)", "Section 303 ( E12 )"):
        match = SECTION_REFERENCE_PATTERN.search(text)
        assert match.group("section") == "303"
        assert match.group("subsection") is None


def test_real_subsection_is_preserved():
    from app.services.claim_validator import SECTION_REFERENCE_PATTERN

    for text in (
        "Section 303(2)",
        "Section 303 subsection (2)",
        "Section 303(2) (E1)",
    ):
        match = SECTION_REFERENCE_PATTERN.search(text)
        assert match.group("subsection") == "(2)"


def test_inline_evidence_marker_is_rejected_explicitly():
    for reference in ("303", "999"):
        answer = LegalAnswer(
            summary=(
                f"Section {reference} (E1): Taking movable property "
                "dishonestly without consent constitutes theft."
            ),
            citations=["E1"],
        )

        result = LegalClaimValidator.validate(
            answer=answer,
            evidence=[make_evidence()],
        )

        assert result.is_valid is False
        assert (
            "inline evidence citation marker"
            in result.claims[0].reason.lower()
        )


def test_actual_subsection_mismatch_still_rejected():
    evidence = make_evidence().model_copy(
        update={"subsection_number": "(2)"}
    )

    for reference, expected_valid in (
        ("303(2)", True),
        ("303(9)", False),
    ):
        answer = LegalAnswer(
            summary=(
                f"Section {reference}: Taking movable property "
                "dishonestly without consent constitutes theft."
            ),
            citations=["E1"],
        )

        result = LegalClaimValidator.validate(
            answer=answer,
            evidence=[evidence],
        )

        assert result.is_valid is expected_valid
