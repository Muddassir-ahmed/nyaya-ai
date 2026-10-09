import pytest

from app.schemas.query_analysis import (
    LegalDomain,
    LegalIntent,
    UrgencyLevel,
)
from app.services.query_analyzer import QueryAnalyzer


@pytest.fixture
def analyzer() -> QueryAnalyzer:
    return QueryAnalyzer()


def test_theft_information_does_not_require_jurisdiction(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "What is the punishment for theft?"
    )

    assert result.intent == LegalIntent.LEGAL_INFORMATION
    assert result.domain == LegalDomain.CRIMINAL
    assert result.urgency == UrgencyLevel.NORMAL
    assert result.jurisdiction is None
    assert result.requires_follow_up is False
    assert result.missing_information == []


def test_stolen_bike_report_requires_jurisdiction(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "Where do I report my stolen bike?"
    )

    assert result.intent == LegalIntent.AUTHORITY_LOOKUP
    assert result.domain == LegalDomain.CRIMINAL
    assert result.jurisdiction is None
    assert result.requires_follow_up is True
    assert "state_or_jurisdiction" in (
        result.missing_information
    )


def test_assam_complaint_does_not_require_follow_up(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "How do I file a complaint against a company in Assam?"
    )

    assert result.intent == LegalIntent.COMPLAINT_GUIDANCE
    assert result.jurisdiction == "AS"
    assert result.requires_follow_up is False
    assert result.missing_information == []


def test_emergency_attack_is_emergency(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "Someone is attacking me right now."
    )

    assert result.intent == LegalIntent.EMERGENCY
    assert result.urgency == UrgencyLevel.EMERGENCY
    assert result.requires_follow_up is False


def test_immediate_death_threat_is_emergency(
    analyzer: QueryAnalyzer,
) -> None:
    result = analyzer.analyze(
        "Someone is threatening to kill me right now "
        "and is standing outside my home."
    )

    assert result.intent == LegalIntent.EMERGENCY
    assert result.urgency == UrgencyLevel.EMERGENCY
    assert result.requires_follow_up is False


@pytest.mark.parametrize(
    "query",
    [
        "Someone threatened to kill me last year.",
        (
            "What is the punishment if someone threatens "
            "to kill another person?"
        ),
    ],
)
def test_non_immediate_death_threat_is_not_emergency(
    analyzer: QueryAnalyzer,
    query: str,
) -> None:
    result = analyzer.analyze(query)

    assert result.intent != LegalIntent.EMERGENCY
    assert result.urgency != UrgencyLevel.EMERGENCY


def test_emergency_does_not_require_jurisdiction(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "I am in immediate danger."
    )

    assert result.intent == LegalIntent.EMERGENCY
    assert result.urgency == UrgencyLevel.EMERGENCY
    assert result.jurisdiction is None
    assert result.requires_follow_up is False


def test_document_guidance_does_not_require_jurisdiction(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "What evidence should I keep?"
    )

    assert result.intent == LegalIntent.DOCUMENT_GUIDANCE
    assert result.requires_follow_up is False


def test_property_procedure_can_require_jurisdiction(
    analyzer: QueryAnalyzer,
) -> None:

    result = analyzer.analyze(
        "How do I evict a tenant?"
    )

    assert result.intent == LegalIntent.LEGAL_PROCEDURE
    assert result.domain == LegalDomain.PROPERTY
    assert result.requires_follow_up is True
    assert "state_or_jurisdiction" in (
        result.missing_information
    )


def test_empty_query_raises_error(
    analyzer: QueryAnalyzer,
) -> None:

    with pytest.raises(ValueError):
        analyzer.analyze("")

def test_firewall_does_not_trigger_criminal_domain():
    analyzer = QueryAnalyzer()

    analysis = analyzer.analyze(
        "How do I configure my firewall?"
    )

    assert analysis.domain == LegalDomain.UNKNOWN

def test_hackathon_does_not_trigger_cybercrime_domain():
    analyzer = QueryAnalyzer()

    analysis = analyzer.analyze(
        "I am participating in a hackathon."
    )

    assert analysis.domain == LegalDomain.UNKNOWN

def test_career_does_not_trigger_traffic_domain():
    analyzer = QueryAnalyzer()

    analysis = analyzer.analyze(
        "I am thinking about changing my career."
    )

    assert analysis.domain == LegalDomain.UNKNOWN

def test_real_hacked_account_still_detects_cybercrime_domain():
    analyzer = QueryAnalyzer()

    analysis = analyzer.analyze(
        "My email account was hacked."
    )

    assert analysis.domain == LegalDomain.CYBERCRIME

def test_where_should_i_complain_routes_to_authority_lookup():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "Where should I complain about a defective "
        "product refund in Assam?"
    )

    assert result.intent == LegalIntent.AUTHORITY_LOOKUP
    assert result.domain == LegalDomain.CONSUMER
    assert result.jurisdiction == "AS"
    assert result.requires_follow_up is False

def test_how_to_make_complaint_remains_complaint_guidance():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "How do I make a consumer complaint in Assam?"
    )

    assert result.intent == LegalIntent.COMPLAINT_GUIDANCE
    assert result.domain == LegalDomain.CONSUMER
    assert result.jurisdiction == "AS"

def test_free_legal_aid_destination_routes_to_authority_lookup():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "Where can I get free legal aid in Assam?"
    )

    assert result.intent == LegalIntent.AUTHORITY_LOOKUP
    assert result.jurisdiction == "AS"
    assert result.requires_follow_up is False

def test_residence_certificate_authority_query():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "Which office should I contact for a "
        "residence certificate in Assam?"
    )

    assert result.intent == LegalIntent.AUTHORITY_LOOKUP
    assert result.domain == LegalDomain.GOVERNMENT_SERVICES
    assert result.jurisdiction == "AS"
    assert result.requires_follow_up is False


def test_public_service_problem_routes_to_general_civic():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "How can I report a problem with a public service?"
    )

    assert result.intent == LegalIntent.GENERAL_CIVIC
    assert result.domain == LegalDomain.GOVERNMENT_SERVICES
    assert result.requires_follow_up is True
    assert "state_or_jurisdiction" in result.missing_information


def test_public_water_supply_problem_routes_to_general_civic():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "How can I complain about an ongoing "
        "public water-supply problem?"
    )

    assert result.intent == LegalIntent.GENERAL_CIVIC
    assert result.domain == LegalDomain.GOVERNMENT_SERVICES
    assert result.requires_follow_up is True


def test_explicit_cat_joke_request_is_out_of_scope():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "Tell me a joke about cats."
    )

    assert result.intent == LegalIntent.OUT_OF_SCOPE
    assert result.domain == LegalDomain.UNKNOWN
    assert result.requires_follow_up is False


def test_generic_government_legal_procedure_remains_legal():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "How can I challenge a government law?"
    )

    assert result.intent == LegalIntent.LEGAL_PROCEDURE
