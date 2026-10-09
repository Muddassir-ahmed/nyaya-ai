from app.services.legal_corpus_context import (
    has_explicit_bns_reference,
)


def test_detects_explicit_bns_short_name():
    assert has_explicit_bns_reference(
        "What does the BNS say about this situation?"
    )


def test_detects_full_bns_name():
    assert has_explicit_bns_reference(
        "Explain this under the Bharatiya Nyaya Sanhita."
    )


def test_does_not_treat_generic_criminal_question_as_explicit_bns():
    assert not has_explicit_bns_reference(
        "What is the punishment for this offence?"
    )
