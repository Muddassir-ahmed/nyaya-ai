from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.citation_validation import (
    GeneratedAnswerCitationValidator,
)


def make_evidence():
    return LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content="Test legal evidence",
        act_name="Bharatiya Nyaya Sanhita, 2023",
        version_label="BNS 2023 — Original",
        section_number="1",
        section_title="Test Section",
        source_name="BNS Gazette",
        source_publisher="Ministry of Home Affairs",
        source_url="https://example.com",
        is_verified=True,
    )


def test_valid_citation():
    evidence = make_evidence()

    answer = LegalAnswer(
        summary="Test answer",
        citations=["E1"],
    )

    result = GeneratedAnswerCitationValidator.validate(
        answer,
        [evidence],
    )

    assert result.is_valid is True
    assert result.citation_completeness == 1.0
    assert len(result.valid_citations) == 1
    assert len(result.invalid_citations) == 0


def test_invalid_citation():
    evidence = make_evidence()

    answer = LegalAnswer(
        summary="Test answer",
        citations=["E99"],
    )

    result = GeneratedAnswerCitationValidator.validate(
        answer,
        [evidence],
    )

    assert result.is_valid is False
    assert result.citation_completeness == 0.0
    assert len(result.invalid_citations) == 1


def test_missing_citations():
    evidence = make_evidence()

    answer = LegalAnswer(
        summary="Test answer.",
        citations=[],
    )

    result = GeneratedAnswerCitationValidator.validate(
        answer,
        [evidence],
    )

    assert result.is_valid is False
    assert result.citation_completeness == 0.0


def test_no_evidence():
    answer = LegalAnswer(
        summary="Test answer.",
        citations=[],
    )

    result = GeneratedAnswerCitationValidator.validate(
        answer,
        [],
    )

    assert result.is_valid is False
    assert result.citation_completeness == 0.0

def test_bracketed_valid_citation_is_normalized():
    evidence = make_evidence()

    answer = LegalAnswer(
        summary="Test answer.",
        citations=["[E1]"],
    )

    result = (
        GeneratedAnswerCitationValidator
        .validate(
            answer,
            [evidence],
        )
    )

    assert result.is_valid is True
    assert result.citation_completeness == 1.0
    assert result.valid_citations == ["E1"]
    assert result.invalid_citations == []


def test_bracketed_unknown_citation_is_rejected():
    evidence = make_evidence()

    answer = LegalAnswer(
        summary="Test answer.",
        citations=["[E99]"],
    )

    result = (
        GeneratedAnswerCitationValidator
        .validate(
            answer,
            [evidence],
        )
    )

    assert result.is_valid is False
    assert result.citation_completeness == 0.0
    assert result.valid_citations == []
    assert result.invalid_citations == [
        "[E99]"
    ]


def test_verbose_fake_citation_is_rejected():
    evidence = make_evidence()

    answer = LegalAnswer(
        summary="Test answer.",
        citations=[
            "The Constitution of India, Article 21"
        ],
    )

    result = (
        GeneratedAnswerCitationValidator
        .validate(
            answer,
            [evidence],
        )
    )

    assert result.is_valid is False