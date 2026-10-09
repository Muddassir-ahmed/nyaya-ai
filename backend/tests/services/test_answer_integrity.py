from app.schemas.legal_answer import (
    LegalAnswer,
)
from app.schemas.legal_evidence import (
    LegalEvidence,
)
from app.services.answer_integrity import (
    LegalAnswerIntegrityValidator,
)


def make_primary_evidence() -> LegalEvidence:
    return LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "A person who commits offence X may be "
            "punished with imprisonment up to three years. "
            "Provided that where the value is below five "
            "thousand rupees, and the person is a first-time "
            "offender, and upon return of the property or "
            "restoration of the property, the person shall "
            "be punished with community service."
        ),
        act_name="Test Act",
        act_short_name="TEST",
        version_label="Test Version",
        section_number="10",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )


def make_special_evidence() -> LegalEvidence:
    return LegalEvidence(
        citation_id="E2",
        chunk_id=2,
        content=(
            "If the offence is committed while causing "
            "serious bodily harm, the person shall be "
            "punished with imprisonment up to ten years."
        ),
        act_name="Test Act",
        act_short_name="TEST",
        version_label="Test Version",
        section_number="20",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )


def test_complete_qualified_rule_passes():
    answer = LegalAnswer(
        summary=(
            "Where the value is below five thousand "
            "rupees, the person is a first-time offender, "
            "and the property is returned or restored, "
            "the person may receive community service."
        ),
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is True
    assert result.issues == []


def test_incomplete_qualified_rule_is_rejected():
    answer = LegalAnswer(
        summary=(
            "Where the value is below five thousand "
            "rupees and the person is a first-time "
            "offender, the person may receive "
            "community service."
        ),
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "incomplete_qualified_rule"
        for issue in result.issues
    )


def test_duplicate_qualified_rule_is_rejected():
    answer = LegalAnswer(
        summary=(
            "Where the value is below five thousand "
            "rupees and the person is a first-time "
            "offender, the person may receive community "
            "service. "
            "Where the value is below five thousand "
            "rupees, the person is a first-time offender, "
            "and the property is returned or restored, "
            "the person may receive community service."
        ),
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    codes = {
        issue.code
        for issue
        in result.issues
    }

    assert (
        "incomplete_qualified_rule"
        in codes
    )

    assert (
        "duplicate_qualified_rule"
        in codes
    )


def test_unrequested_special_penalty_rule_is_rejected():
    answer = LegalAnswer(
        summary=(
            "The general punishment is imprisonment "
            "up to three years. "
            "If the offence causes serious bodily harm, "
            "the punishment may extend to ten years."
        ),
        citations=["E1", "E2"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
                make_special_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "unrequested_special_rule"
        for issue in result.issues
    )


def test_special_rule_is_allowed_when_query_supplies_trigger():
    answer = LegalAnswer(
        summary=(
            "If the offence causes serious bodily harm, "
            "the person may face imprisonment up to "
            "ten years."
        ),
        citations=["E2"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment if offence X "
                "causes serious bodily harm?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
                make_special_evidence(),
            ],
        )
    )

    assert result.is_valid is True

def test_incomplete_qualified_rule_in_legal_basis_is_rejected():
    answer = LegalAnswer(
        summary=(
            "A person who commits offence X may be "
            "punished with imprisonment up to three years."
        ),
        legal_basis=[
            (
                "Where the value is below five thousand "
                "rupees and the person is a first-time "
                "offender, the person may receive "
                "community service."
            )
        ],
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "incomplete_qualified_rule"
        for issue in result.issues
    )


def test_changed_numeric_qualifier_is_rejected():
    answer = LegalAnswer(
        summary=(
            "Where the value is below six thousand "
            "rupees, the person is a first-time offender, "
            "and the property is returned or restored, "
            "the person may receive community service."
        ),
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "mismatched_numeric_value"
        for issue in result.issues
    )


def test_single_incidental_special_word_does_not_authorize_special_rule():
    answer = LegalAnswer(
        summary=(
            "The general punishment is imprisonment "
            "up to three years. "
            "If the offence is committed while causing "
            "serious bodily harm, the person shall be "
            "punished with imprisonment up to ten years."
        ),
        citations=["E1", "E2"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X "
                "involving harm?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
                make_special_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "unrequested_special_rule"
        for issue in result.issues
    )

def test_broad_penalty_query_rejects_omitted_qualified_rule():
    answer = LegalAnswer(
        summary=(
            "A person who commits offence X may be "
            "punished with imprisonment up to three years."
        ),
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    assert any(
        issue.code
        == "omitted_qualified_rule"
        for issue in result.issues
    )

def test_present_complete_qualified_rule_is_not_reported_as_omitted():
    answer = LegalAnswer(
        summary=(
            "Where the value is below five thousand "
            "rupees and the person is a first-time "
            "offender, the person may receive "
            "community service. "
            "Where the value is below five thousand "
            "rupees, the person is a first-time offender, "
            "and the property is returned or restored, "
            "the person may receive community service."
        ),
        citations=["E1"],
    )

    result = (
        LegalAnswerIntegrityValidator.validate(
            user_query=(
                "What is the punishment for offence X?"
            ),
            answer=answer,
            evidence=[
                make_primary_evidence(),
            ],
        )
    )

    assert result.is_valid is False

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        "incomplete_qualified_rule"
        in codes
    )

    assert (
        "duplicate_qualified_rule"
        in codes
    )

    assert (
        "omitted_qualified_rule"
        not in codes
    )

def _check_repeat_rule_diagnostic(summary):
    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=(
            "In case of second or subsequent conviction of any "
            "person under this section, he shall be punished with "
            "rigorous imprisonment for a term which shall not be "
            "less than one year but which may extend to five years "
            "and with fine."
        ),
    )

    return LegalAnswerIntegrityValidator.validate(
        user_query="What is the punishment involving imprisonment?",
        answer=LegalAnswer(
            summary=summary,
            citations=["E1"],
        ),
        evidence=[evidence],
    )


def test_partial_repeat_rule_is_blocked_as_incomplete():
    summary = (
        "Subsequent convictions carry rigorous imprisonment "
        "of at least one year but up to five years and a fine."
    )

    result = _check_repeat_rule_diagnostic(summary)

    assert result.is_valid is False
    assert [issue.code for issue in result.issues] == [
        "incomplete_qualified_rule"
    ]
    assert result.issues[0].claim == summary


def test_absent_repeat_rule_still_blocked_as_omitted():
    result = _check_repeat_rule_diagnostic(
        "The general punishment is imprisonment up to three years."
    )

    assert result.is_valid is False
    assert "omitted_qualified_rule" in {
        issue.code for issue in result.issues
    }


def test_consequence_alone_does_not_establish_rule_presence():
    result = _check_repeat_rule_diagnostic(
        "Rigorous imprisonment of at least one year but up to "
        "five years and a fine applies."
    )

    assert result.is_valid is False
    assert "omitted_qualified_rule" in {
        issue.code for issue in result.issues
    }


def test_single_condition_word_does_not_establish_rule_presence():
    result = _check_repeat_rule_diagnostic(
        "Conviction carries rigorous imprisonment of at least "
        "one year but up to five years and a fine."
    )

    assert result.is_valid is False
    assert "omitted_qualified_rule" in {
        issue.code for issue in result.issues
    }
