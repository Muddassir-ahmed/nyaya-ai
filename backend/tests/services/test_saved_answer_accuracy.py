"""Offline regressions from saved NyayaAI diagnostics.

Evidence content: captured 2026-09-19; answers: provider-content entries
from 2026-09-22 14:34:20 and 14:52:48 uploads. Text is preserved, including
pasted spacing artifacts. No database, network, or Ollama calls.

These assertions require the known accuracy gaps to be rejected.
The corrected controls are editorial test variants, not model outputs.
"""
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.claim_validator import LegalClaimValidator
from app.services.answer_integrity import LegalAnswerIntegrityValidator

CAPTURED_EVIDENCE = [{'citation_id': 'E1',
  'chunk_id': 4392,
  'section_number': '303',
  'content': 'Section 303\n'
             'Subsection (2)\n'
             '\n'
             'Whoever commits theft shall be punished with imprisonment of either '
             'description for a term which may extend to three years, or with fine, or '
             'with both and in case of second or subsequent conviction of any person '
             'under this section, he shall be punished with rigorous imprisonment for '
             'a term which shall not be less than one year but which may extend to '
             'five years and with fine:\n'
             '\n'
             'Provided that in cases of theft where the value of the stolen property '
             'is less than five thousand rupees, and a person is convicted for the '
             'first time, shall upon return of the value of property or restoration of '
             'the stolen property,shall be punished with community service.'},
 {'citation_id': 'E2',
  'chunk_id': 4397,
  'section_number': '307',
  'content': 'Section 307\n'
             '\n'
             'Whoever commits theft, having made preparation for causing death, or '
             'hurt, orrestraint, or fear of death, or of hurt, or of restraint, to any '
             'person, in order to the committing of such theft, or in order to the '
             'effecting of his escape after the committing of such theft, or in order '
             'to the retaining of property taken by such theft, shall be punished with '
             'rigorous imprisonment for a termwhich may extend to ten years, and shall '
             'also be liable to fine.'},
 {'citation_id': 'E3',
  'chunk_id': 4115,
  'section_number': '134',
  'content': 'Section 134\n'
             '\n'
             'Whoever assaults or uses criminal force to any person, in attempting to '
             'commit theft on any property which that person is then wearing or '
             'carrying, shall be punished with imprisonment of either description for '
             'a term which may extendto two years, or with fine, or with both.'},
 {'citation_id': 'E4',
  'chunk_id': 4396,
  'section_number': '306',
  'content': 'Section 306\n'
             '\n'
             'Whoever, being a clerk or servant, or being employed in the capacity of '
             'a clerk or servant, commits theft in respect of any property in the '
             'possession of his master or employer, shall be punished with '
             'imprisonment of either description for a term which may extend to seven '
             'years, and shall also be liable to fine.'},
 {'citation_id': 'E5',
  'chunk_id': 4467,
  'section_number': '328',
  'content': 'Section 328\n'
             '\n'
             'Whoever intentionally runs any vessel aground or ashore, intending to '
             'commit theft of any property contained therein or to dishonestly '
             'misappropriate any such property, or with intent that such theft or '
             'misappropriation of property may be committed, shall be punished with '
             'imprisonment of either description fora term which may extend to ten '
             'years, and shall also be liable to fine.'}]

SOFTENED_ANSWER = {'summary': 'The punishment for theft under the Bharatiya Nyaya Sanhita, 2023, is '
            'imprisonment for a term which may extend to three years, or with fine, or '
            'with both. For a second or subsequent conviction, the punishment is '
            'rigorous imprisonment for a term which shall not be less than one year '
            'but whichmay extend to five years, and with fine. If the value of the '
            'stolen property is less than five thousand rupees and the person is '
            'convicted for the first time, uponreturn of the value of property or '
            'restoration of the stolen property, the punishment may include community '
            'service.',
 'legal_basis': ['Under Section 303,whoever commits theft shall be punished with '
                 'imprisonment of either description for a term which may extend to '
                 'three years, or with fine, or with both. In case of second or '
                 'subsequent conviction, he shall be punished with rigorous '
                 'imprisonment for a term which shall not be less than one year but '
                 'which may extend to five yearsand with fine.',
                 'Provided that in cases of theft where the value of the stolen '
                 'property is less than five thousand rupees, and a person is '
                 'convicted for the first time, upon return of the value of property '
                 'or restoration of the stolen property, he shall be punished with '
                 'community service.'],
 'possible_options': [],
 'evidence_to_preserve': [],
 'next_steps': [],
 'caveats': ['The punishment may vary depending on the value of the stolen property '
             'and whether it isa first-time or subsequent conviction.'],
 'citations': ['E1']}

MIXED_ANSWER = {'summary': 'The punishment for theft under the Bharatiya Nyaya Sanhita, 2023, depends '
            'on the circumstances of the case. For a first-time conviction where the '
            'value of the stolen property is less than five thousand rupees and the '
            'property is returned or restored, the punishment may include community '
            'service. For a first-time conviction where the value of the stolen '
            'property is five thousand rupees or more, the punishment may include '
            'imprisonment of up to three years, or a fine, or both. For a second or '
            'subsequent conviction, the punishment may include rigorous imprisonment '
            'for a term of at least one year but not exceeding five years, and a fine. '
            'If the theft involves preparation for causing death, hurt, or fear of '
            'death, or if it involves assault or criminal force during the attempt, '
            'the punishment may include rigorous imprisonment for up to ten years and '
            'a fine. Ifthe theft is committed by a clerk or servant in relation to '
            'property of their master or employer, the punishment may include '
            'imprisonment of up to seven years and a fine.',
 'legal_basis': ['Under Section 303, whoever commits theft shallbe punished with '
                 'imprisonment of either description for a term which may extend to '
                 'three years, or with fine, or with both. In case of second or '
                 'subsequent conviction, he shall be punished with rigorous '
                 'imprisonment for a term which shall not beless than one year but '
                 'which may extend to five years and with fine. Provided that in cases '
                 'of theft where the value of the stolen property is less than five '
                 'thousand rupees, and a person is convicted for the first time, upon '
                 'return of the valueof property or restoration of the stolen '
                 'property, he shall be punished with community service.',
                 'Under Section 307, whoever commits theft, having made preparation '
                 'for causing death, or hurt, or restraint, or fear of death, or of '
                 'hurt, or of restraint, to any person, in order to the committing of '
                 'such theft, or in orderto the effecting of his escape after the '
                 'committing of such theft, or in order tothe retaining of property '
                 'taken by such theft, shall be punished with rigorous imprisonment '
                 'for a term which may extend to ten years, and shall also be liable '
                 'to fine.',
                 'Under Section 134, whoever assaults or uses criminal force to any '
                 'person, in attempting to commit theft on any property which that '
                 'person is then wearing or carrying, shall be punished with '
                 'imprisonment of either description for a term which may extend to '
                 'two years, or with fine, or with both.',
                 'Under Section 306, whoever, being a clerk or servant, or being '
                 'employed in the capacity of a clerk or servant, commits theft in '
                 'respect of any property in the possession of hismaster or employer, '
                 'shall be punished with imprisonment of either description fora term '
                 'which may extend to seven years, and shall also be liable to fine.'],
 'possible_options': [],
 'evidence_to_preserve': [],
 'next_steps': [],
 'caveats': ['The punishment for theft may vary depending on the specific '
             'circumstances of the case, including the value of the stolen property, '
             'the presence of assault or criminal force, and whether the theft is '
             'committed by a clerk or servant.'],
 'citations': ['E1', 'E2', 'E3', 'E4']}

def evidence():
    return [LegalEvidence(**item) for item in CAPTURED_EVIDENCE]


def claims_valid(answer):
    return LegalClaimValidator.validate(answer=answer, evidence=evidence()).is_valid


def integrity_valid(answer):
    return LegalAnswerIntegrityValidator.validate(
        user_query="What is the punishment for theft?",
        answer=answer,
        evidence=evidence(),
    ).is_valid


def test_softened_mandatory_consequence_is_rejected():
    answer = LegalAnswer(**SOFTENED_ANSWER)
    assert not (claims_valid(answer) and integrity_valid(answer)), (
        "Both validators accepted 'may include community service' "
        "despite the mandatory consequence in the captured evidence."
    )


def test_corrected_mandatory_consequence_is_accepted():
    answer = LegalAnswer(**SOFTENED_ANSWER)
    original = "the punishment may include community service"
    assert original in answer.summary
    answer.summary = answer.summary.replace(
        original, "the punishment is community service"
    )
    assert claims_valid(answer)
    assert integrity_valid(answer)


MIXED_SENTENCE = (
    "If the theft involves preparation for causing death, hurt, or fear of death, "
    "or if it involves assault or criminal force during the attempt, the "
    "punishment may include rigorous imprisonment for up to ten years and a fine."
)


def test_mixed_provision_punishment_is_rejected_by_claim_validation():
    answer = LegalAnswer(**MIXED_ANSWER)
    assert MIXED_SENTENCE in answer.summary
    # Isolate the numeric error from the summary's separate modality errors.
    answer.summary = MIXED_SENTENCE
    result = LegalClaimValidator.validate(answer=answer, evidence=evidence())
    assert not result.is_valid
    assert "maximum penalty duration" in result.claims[0].reason


def test_separated_provision_punishments_are_accepted_by_claim_validation():
    answer = LegalAnswer(**MIXED_ANSWER)
    assert MIXED_SENTENCE in answer.summary
    # These two captured propositions give separate circumstances/penalties.
    # Scope for the broad query is deliberately not tested here.
    answer.summary = answer.legal_basis[1] + " " + answer.legal_basis[2]
    assert claims_valid(answer)


def test_live_theft_answer_omitting_restoration_condition_is_rejected():
    answer = LegalAnswer(
        summary=(
            "The punishment for theft under Section 303 of the "
            "Bharatiya Nyaya Sanhita, 2023, is imprisonment of "
            "either description for a term which may extend to "
            "three years, or with fine, or with both. In case of "
            "second or subsequent conviction, the punishment is "
            "rigorous imprisonment for a term which shall not be "
            "less than one year but which may extend to five years "
            "and with fine. Additionally, if the value of the stolen "
            "property is less than five thousand rupees, and a person "
            "is convicted for the first time, they shall be punished "
            "with community service."
        ),
        citations=["E1"],
    )

    result = LegalAnswerIntegrityValidator.validate(
        user_query="What is the punishment for theft?",
        answer=answer,
        evidence=evidence(),
    )

    assert result.is_valid is False
    assert "incomplete_qualified_rule" in {
        issue.code for issue in result.issues
    }
