from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.answer_integrity import LegalAnswerIntegrityValidator as V


def repeat_evidence():
    return LegalEvidence(
        citation_id='E1', chunk_id=1, section_number='303',
        content=(
            'In case of second or subsequent conviction of any person under this section, '
            'he shall be punished with rigorous imprisonment for a term which shall not '
            'be less than one year but which may extend to five years and with fine.'
        ),
    )


def test_other_theft_rule_does_not_trigger_repeat_numeric_mismatch():
    statement = (
        'Under Section 307, whoever commits theft, having made preparation for causing '
        'death, or hurt, or restraint, or fear of death, or of hurt, or of restraint, '
        'to any person, in order to the committing of such theft, or in order to the '
        'effecting of his escape after the committing of such theft, or in order to '
        'the retainingof property taken by such theft, shall be punished with rigorous '
        'imprisonment fora term which may extend to ten years, and shall also be liable to fine.'
    )
    issues = V._qualifier_issues(LegalAnswer(summary=statement), [repeat_evidence()])
    assert not issues


def test_numeric_condition_error_still_detected():
    statement = (
        'Under Section 303, in case of third or subsequent conviction of any person '
        'under this section, he shall be punished with rigorous imprisonment for a '
        'term which shall not be less than one year but which may extend to five years '
        'and with fine.'
    )
    issues = V._qualifier_issues(LegalAnswer(summary=statement), [repeat_evidence()])
    assert any(i.code == 'mismatched_numeric_value' and i.citation_id == 'E1' for i in issues)


def test_different_section_label_does_not_bypass_condition_check():
    statement = (
        'Under Section 307, in case of third or subsequent conviction of any person '
        'under this section, he shall be punished with rigorous imprisonment for a '
        'term which shall not be less than one year but which may extend to five years '
        'and with fine.'
    )
    issues = V._qualifier_issues(LegalAnswer(summary=statement), [repeat_evidence()])
    assert any(i.code == 'mismatched_numeric_value' for i in issues)


def test_correct_repeat_rule_still_matches():
    evidence = repeat_evidence()
    rule = V._extract_qualified_rules(evidence)[0]
    assert V._statement_matches_rule(evidence.content, rule)
    assert not V._qualifier_issues(LegalAnswer(summary=evidence.content), [evidence])
