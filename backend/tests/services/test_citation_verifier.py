from app.schemas.legal_evidence import LegalEvidence
from app.services.citation_verifier import (
    verify_legal_evidence,
)


def make_valid_evidence() -> LegalEvidence:
    return LegalEvidence(
        chunk_id=1,
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


def test_valid_evidence_is_verified():

    evidence = make_valid_evidence()

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is True

    assert result.has_source is True
    assert result.has_source_url is True
    assert result.has_act is True
    assert result.has_version is True
    assert result.has_section is True
    assert result.document_verified is True

    assert result.citation_text is not None


def test_unverified_document_is_rejected():

    evidence = make_valid_evidence()

    evidence.is_verified = False

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is False
    assert result.document_verified is False
    assert result.citation_text is None


def test_missing_source_url_is_rejected():

    evidence = make_valid_evidence()

    evidence.source_url = None

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is False
    assert result.has_source_url is False


def test_missing_section_is_rejected():

    evidence = make_valid_evidence()

    evidence.section_number = None

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is False
    assert result.has_section is False

def test_constitution_preamble_document_level_is_valid():
    evidence = LegalEvidence(
        chunk_id=3027,
        content=(
            "The Constitution of India\n"
            "Preamble\n\n"
            "WE, THE PEOPLE OF INDIA, having solemnly "
            "resolved to constitute India into a "
            "SOVEREIGN SOCIALIST SECULAR DEMOCRATIC "
            "REPUBLIC."
        ),
        document_title="The Constitution of India",
        document_type="constitution",
        act_name="The Constitution of India",
        act_short_name="COI",
        version_label=(
            "Constitution of India — As on 1 May 2026"
        ),
        section_number=None,
        source_name=(
            "Constitution of India — Official "
            "English Edition"
        ),
        source_publisher=(
            "Legislative Department, Ministry of "
            "Law and Justice, Government of India"
        ),
        source_url="https://example.com/constitution.pdf",
        is_verified=True,
    )

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is True
    assert result.has_section is False
    assert result.citation_text is not None
    assert "Preamble" in result.citation_text

def test_constitution_schedule_document_level_is_valid():
    evidence = LegalEvidence(
        chunk_id=999,
        content=(
            "The Constitution of India\n"
            "Seventh Schedule\n"
            "Schedule number: 7\n\n"
            "List I — Union List"
        ),
        document_title="The Constitution of India",
        document_type="constitution",
        act_name="The Constitution of India",
        act_short_name="COI",
        version_label=(
            "Constitution of India — As on 1 May 2026"
        ),
        section_number=None,
        source_name="Official Constitution",
        source_publisher=(
            "Legislative Department, Ministry of "
            "Law and Justice, Government of India"
        ),
        source_url="https://example.com/constitution.pdf",
        is_verified=True,
    )

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is True
    assert result.has_section is False
    assert result.citation_text is not None
    assert "Seventh Schedule" in result.citation_text

def test_unknown_constitution_document_level_chunk_is_rejected():
    evidence = LegalEvidence(
        chunk_id=999,
        content=(
            "The Constitution of India\n"
            "Unknown material\n"
            "Some text."
        ),
        document_title="The Constitution of India",
        document_type="constitution",
        act_name="The Constitution of India",
        act_short_name="COI",
        version_label=(
            "Constitution of India — As on 1 May 2026"
        ),
        section_number=None,
        source_name="Official Constitution",
        source_publisher=(
            "Legislative Department, Ministry of "
            "Law and Justice, Government of India"
        ),
        source_url="https://example.com/constitution.pdf",
        is_verified=True,
    )

    result = verify_legal_evidence(
        evidence
    )

    assert result.is_valid is False
