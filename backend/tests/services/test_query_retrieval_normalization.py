from app.schemas.query_analysis import (
    LegalDomain,
)
from app.services.query_analyzer import (
    QueryAnalyzer,
)


def test_explicit_bns_question_is_classified_as_criminal_law():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "What is the provision for mob lynching under the BNS?"
    )

    assert result.domain == LegalDomain.CRIMINAL


def test_generic_commits_theft_query_gets_canonical_retrieval_query():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "What happens if a person commits theft?"
    )

    assert (
        result.domain
        == LegalDomain.CRIMINAL
    )

    assert (
        result.rewritten_queries[0]
        == "punishment for theft"
    )

    assert (
        "what happens if a person commits theft?"
        in result.rewritten_queries
    )


def test_stealing_property_is_normalized_as_criminal_theft_query():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "Punishment for stealing property"
    )

    assert (
        result.domain
        == LegalDomain.CRIMINAL
    )

    assert (
        result.rewritten_queries[0]
        == "punishment for theft"
    )

    assert (
        "punishment for stealing property"
        in result.rewritten_queries
    )


def test_theft_definition_gets_concise_canonical_retrieval_query():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "What is theft under the Bharatiya Nyaya Sanhita?"
    )

    assert result.domain == LegalDomain.CRIMINAL
    assert result.rewritten_queries[0] == "theft"
    assert (
        "what is theft under the bharatiya nyaya sanhita?"
        in result.rewritten_queries
    )


def test_theft_definition_alias_is_normalized_to_theft():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "What is the meaning of stealing?"
    )

    assert result.domain == LegalDomain.CRIMINAL
    assert result.rewritten_queries[0] == "theft"


def test_penalty_query_keeps_penalty_canonicalization_priority():
    analyzer = QueryAnalyzer()

    result = analyzer.analyze(
        "What is the punishment for theft?"
    )

    assert result.domain == LegalDomain.CRIMINAL
    assert result.rewritten_queries[0] == "punishment for theft"


def test_qualified_dwelling_theft_definition_preserves_context():
    analyzer = QueryAnalyzer()
    query = "What is theft committed in a human dwelling?"

    result = analyzer.analyze(query)

    assert result.domain == LegalDomain.CRIMINAL
    assert result.rewritten_queries[0] == query.lower()
    assert result.rewritten_queries[0] != "theft"


def test_qualified_clerk_theft_definition_preserves_context():
    analyzer = QueryAnalyzer()
    query = "What is theft by a clerk or servant from an employer?"

    result = analyzer.analyze(query)

    assert result.domain == LegalDomain.CRIMINAL
    assert result.rewritten_queries[0] == query.lower()
    assert result.rewritten_queries[0] != "theft"


def test_unprovoked_hitting_preserves_negative_qualifier_in_retrieval():
    analyzer = QueryAnalyzer()
    query = (
        "A person intentionally hit me without any provocation. "
        "Which BNS provisions may apply?"
    )

    result = analyzer.analyze(query)

    assert result.domain == LegalDomain.CRIMINAL
    assert result.rewritten_queries[0] == (
        "assault or criminal force otherwise than on "
        "grave and sudden provocation"
    )
    assert query.lower() in result.rewritten_queries
