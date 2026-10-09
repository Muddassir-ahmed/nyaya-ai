from app.schemas.legal_evidence import LegalEvidence
from app.services.legal_prompt import (
    SYSTEM_PROMPT,
    build_grounded_prompt,
)


def make_evidence() -> LegalEvidence:

    return LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "A person commits an offence when "
            "the conditions specified by this "
            "provision are satisfied."
        ),

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


def test_system_prompt_contains_grounding_rules():

    assert (
        "ONLY on the legal evidence"
        in SYSTEM_PROMPT
    )

    assert (
        "Do not invent"
        in SYSTEM_PROMPT
    )

    assert (
        "Never claim that you are a lawyer"
        in SYSTEM_PROMPT
    )


def test_grounded_prompt_contains_user_question():

    evidence = [make_evidence()]

    prompt = build_grounded_prompt(
        user_query="What is theft?",
        evidence=evidence,
    )

    assert "What is theft?" in prompt


def test_grounded_prompt_contains_evidence():

    evidence = [make_evidence()]

    prompt = build_grounded_prompt(
        user_query="What is theft?",
        evidence=evidence,
    )

    assert (
        "Bharatiya Nyaya Sanhita, 2023"
        in prompt
    )

    assert "Section: 303" in prompt

    assert "Theft" in prompt

    assert (
        "A person commits an offence"
        in prompt
    )


def test_grounded_prompt_requires_structured_json():
    from app.schemas.legal_answer import LegalAnswer

    evidence = [make_evidence()]

    response_schema = (
        LegalAnswer.model_json_schema()
    )

    prompt = build_grounded_prompt(
        user_query="What is theft?",
        evidence=evidence,
        response_schema=response_schema,
    )

    assert (
        "Return ONLY one valid JSON object."
        in prompt
    )

    assert (
        "Do not return Markdown."
        in prompt
    )

    assert (
        "Do not add text before the JSON."
        in prompt
    )

    assert (
        "Do not add text after the JSON."
        in prompt
    )

    assert '"summary"' in prompt
    assert '"legal_basis"' in prompt
    assert '"possible_options"' in prompt
    assert '"evidence_to_preserve"' in prompt
    assert '"next_steps"' in prompt
    assert '"caveats"' in prompt
    assert '"citations"' in prompt