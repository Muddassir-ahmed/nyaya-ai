from app.schemas.legal_evidence import (
    LegalEvidence,
)
from app.services.legal_prompt import (
    SYSTEM_PROMPT,
    build_grounded_prompt,
)


def make_conditional_evidence() -> LegalEvidence:
    return LegalEvidence(
        chunk_id=1,
        content=(
            "A person is subject to consequence X. "
            "Provided that where condition A and "
            "condition B are satisfied, consequence Y applies."
        ),
        act_name="Test Act",
        act_short_name="TEST",
        version_label="Test Version",
        section_number="1",
        section_title="Test Section",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )


def test_system_prompt_requires_material_conditions_to_be_preserved():
    prompt = SYSTEM_PROMPT.lower()

    assert "all material conditions" in prompt
    assert "qualified consequence" in prompt
    assert "possible option" in prompt
    assert "unnecessary repetition" in prompt
    assert "factual polarity" in prompt
    assert "no provocation" in prompt


def test_grounded_prompt_contains_qualifier_completeness_instruction():
    prompt = build_grounded_prompt(
        user_query="What is the consequence?",
        evidence=[
            make_conditional_evidence()
        ],
    ).lower()

    normalized_prompt = " ".join(
        prompt.split()
    )

    assert "important qualifier rule" in normalized_prompt
    assert "provided that" in normalized_prompt

    assert (
        "preserve all of those material conditions "
        "together in the answer"
        in normalized_prompt
    )

    assert (
        'do not convert a condition into a '
        '"possible option"'
        in normalized_prompt
    )

    assert "condition a" in normalized_prompt
    assert "condition b" in normalized_prompt
    assert "consequence y" in normalized_prompt
    assert "explicitly states the opposite condition" in normalized_prompt

def test_grounded_prompt_defines_structured_field_semantics():
    prompt = build_grounded_prompt(
        user_query="What is the punishment?",
        evidence=[
            make_conditional_evidence()
        ],
    ).lower()

    normalized_prompt = " ".join(
        prompt.split()
    )

    assert (
        "general/base rule first"
        in normalized_prompt
    )

    assert (
        "punishments, sentences, penalties, "
        "statutory prerequisites"
        in normalized_prompt
    )

    assert (
        "legal authority, not user evidence to preserve"
        in normalized_prompt
    )

    assert (
        "never transform a statutory prerequisite"
        in normalized_prompt
    )

    assert (
        "final completeness check"
        in normalized_prompt
    )

    assert (
        "every statement of y must preserve a + b + c"
        in normalized_prompt
    )
