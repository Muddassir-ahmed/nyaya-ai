"""Offline policy and generator tests. No DB or Ollama calls."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.schemas.claim_validation import ClaimSupportLevel, ClaimValidation, ClaimValidationResult
from app.schemas.answer_integrity import AnswerIntegrityResult, AnswerIntegrityIssue
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.penalty_retry import penalty_retry_feedback
from app.services.legal_qualifier_grounding import (
    PROVOCATION_CONDITION_MISMATCH_REASON,
)
from app.services.legal_answer_generator import LegalAnswerGenerator
import app.services.query_orchestrator as qo

DURATION = ('A stated maximum penalty duration does not match the cited evidence '
            'for one of its stated circumstances.')
MODALITY = ('A mandatory penalty consequence in the cited evidence was presented '
            'as discretionary.')
QUALIFIER = PROVOCATION_CONDITION_MISMATCH_REASON


def claim_result(*reasons):
    claims = [ClaimValidation(claim=f'Rejected statement {i}', citation_ids=['E1'],
              support_level=ClaimSupportLevel.UNSUPPORTED, reason=r)
              for i, r in enumerate(reasons)]
    return ClaimValidationResult(is_valid=not reasons, claims=claims,
                                 unsupported_claims=[c.claim for c in claims])


def integrity(valid):
    return AnswerIntegrityResult(is_valid=valid, issues=[] if valid else [
        AnswerIntegrityIssue(code='unrequested_special_rule', message='Unrelated rule', citation_id='E1')])


def test_both_known_penalty_errors_get_explicit_feedback():
    feedback = penalty_retry_feedback(claim_result(DURATION, MODALITY))
    assert [x['code'] for x in feedback] == ['penalty_duration_mismatch', 'mandatory_penalty_softened']
    assert feedback[1]['claim'] == 'Rejected statement 1'


def test_mixed_unrelated_failure_disables_penalty_retry():
    assert penalty_retry_feedback(claim_result(DURATION, 'Unrelated unsupported claim.')) == []


def test_changed_reason_fails_closed():
    assert penalty_retry_feedback(claim_result(DURATION + ' extra text')) == []


def test_inconsistent_failure_result_fails_closed():
    result = claim_result(DURATION)
    result.unsupported_claims = []
    assert penalty_retry_feedback(result) == []


def test_no_failures_produce_no_penalty_feedback():
    assert penalty_retry_feedback(claim_result()) == []


def test_provocation_condition_failure_gets_bounded_feedback():
    feedback = penalty_retry_feedback(claim_result(QUALIFIER))
    assert feedback == [
        {
            'code': 'provocation_condition_mismatch',
            'claim': 'Rejected statement 0',
        }
    ]


def run_case(initial_claim, final_claim=None, initial_citation=True,
             final_citation=True, initial_integrity=False, final_integrity=True):
    analysis = SimpleNamespace(intent=object(), requires_follow_up=False)
    evidence = [LegalEvidence(citation_id='E1', chunk_id=1, content='Verified text.')]
    retrieval = SimpleNamespace(exact_reference_status=None, retrieval_performed=True,
                                analysis=analysis, chunks=[], retrieval_reason='test')
    draft = LegalAnswer(summary='A test draft.', citations=['E1'])
    generator = SimpleNamespace(generate=AsyncMock(return_value=draft))
    orchestrator = qo.QueryOrchestrator.__new__(qo.QueryOrchestrator)
    orchestrator.query_analyzer = SimpleNamespace(analyze=lambda query: analysis)
    orchestrator.legal_retrieval_orchestrator = SimpleNamespace(retrieve=AsyncMock(return_value=retrieval))
    orchestrator.legal_answer_generator = generator
    build = AsyncMock(return_value=evidence)
    counts = {'claim': [], 'citation': [], 'integrity': []}

    def choose(kind, first, second):
        attempt = generator.generate.await_count
        counts[kind].append(attempt)
        return first if attempt == 1 else second

    with patch.object(qo, 'build_legal_evidence', build), \
         patch.object(qo, 'verify_evidence_list', return_value=[SimpleNamespace(evidence=evidence[0])]), \
         patch.object(qo.GeneratedAnswerCitationValidator, 'validate', side_effect=lambda **kw:
                      SimpleNamespace(is_valid=choose('citation', initial_citation, final_citation))), \
         patch.object(qo.LegalClaimValidator, 'validate', side_effect=lambda **kw:
                      choose('claim', initial_claim, final_claim or claim_result())), \
         patch.object(qo.LegalAnswerIntegrityValidator, 'validate', side_effect=lambda **kw:
                      integrity(choose('integrity', initial_integrity, final_integrity))):
        result = asyncio.run(orchestrator.handle(db=object(), query='What is the punishment?'))
    assert orchestrator.legal_retrieval_orchestrator.retrieve.await_count == 1
    assert build.await_count == 1
    calls = generator.generate.await_args_list
    if len(calls) == 2:
        assert calls[0].kwargs['evidence'] is calls[1].kwargs['evidence']
        assert all(2 in attempts for attempts in counts.values())
        assert calls[1].kwargs['retry_mode'] is True
    return result, calls


def test_penalty_failure_can_be_corrected_once():
    result, calls = run_case(claim_result(DURATION, MODALITY))
    assert not result.answer_blocked
    assert len(calls) == 2
    assert len(calls[1].kwargs['claim_corrections']) == 2


def test_provocation_condition_failure_can_be_corrected_once():
    result, calls = run_case(claim_result(QUALIFIER), initial_integrity=True)
    assert not result.answer_blocked
    assert len(calls) == 2
    assert calls[1].kwargs['claim_corrections'][0]['code'] == (
        'provocation_condition_mismatch'
    )


def test_penalty_failure_can_retry_when_integrity_already_passes():
    result, calls = run_case(claim_result(MODALITY), initial_integrity=True)
    assert not result.answer_blocked
    assert len(calls) == 2


def test_repeated_penalty_failure_stays_blocked_without_third_attempt():
    result, calls = run_case(claim_result(DURATION), final_claim=claim_result(DURATION))
    assert result.answer_blocked
    assert len(calls) == 2


def test_invalid_initial_citations_never_retry():
    result, calls = run_case(claim_result(DURATION), initial_citation=False)
    assert result.answer_blocked
    assert len(calls) == 1


def test_unknown_claim_failure_never_retries():
    result, calls = run_case(claim_result('Unrelated unsupported claim.'))
    assert result.answer_blocked
    assert len(calls) == 1


def test_mixed_claim_failures_never_retry():
    result, calls = run_case(claim_result(DURATION, 'Unrelated unsupported claim.'))
    assert result.answer_blocked
    assert len(calls) == 1


def test_invalid_retry_citations_stay_blocked():
    result, calls = run_case(claim_result(DURATION), final_citation=False)
    assert result.answer_blocked
    assert len(calls) == 2


def test_invalid_retry_integrity_stays_blocked():
    result, calls = run_case(claim_result(DURATION), final_integrity=False)
    assert result.answer_blocked
    assert len(calls) == 2


def test_existing_integrity_only_retry_still_works():
    result, calls = run_case(claim_result())
    assert not result.answer_blocked
    assert len(calls) == 2
    assert 'claim_corrections' not in calls[1].kwargs


def test_valid_first_draft_is_not_retried():
    result, calls = run_case(claim_result(), initial_integrity=True)
    assert not result.answer_blocked
    assert len(calls) == 1


def capture_request(retry_mode):
    answer = LegalAnswer(summary='Test response.', citations=['E1'])
    provider = SimpleNamespace(generate=AsyncMock(return_value=SimpleNamespace(content=answer.model_dump_json())))
    generator = LegalAnswerGenerator(provider)
    evidence = [LegalEvidence(citation_id='E1', chunk_id=1, content='Verified text.')]
    feedback = penalty_retry_feedback(claim_result(DURATION, MODALITY))
    result = asyncio.run(generator.generate(user_query='What is the punishment?', evidence=evidence,
                         retry_mode=retry_mode, integrity_issue_codes=['unrequested_special_rule'],
                         claim_corrections=feedback))
    assert result == answer
    assert provider.generate.await_count == 1
    return provider.generate.await_args.args[0], feedback


def test_generator_sends_penalty_feedback_only_on_retry():
    request, feedback = capture_request(True)
    user_prompt = request.messages[-1].content
    assert json.dumps(feedback, ensure_ascii=False) in user_prompt
    assert 'TARGETED CLAIM CORRECTION:' in user_prompt
    assert 'TARGETED CORRECTION FOR unrequested_special_rule:' in user_prompt
    assert 'may extend' in user_prompt


def test_generator_first_attempt_does_not_use_retry_feedback():
    request, _ = capture_request(False)
    assert 'TARGETED CLAIM CORRECTION:' not in request.messages[-1].content


def test_generator_sends_provocation_condition_feedback_on_retry():
    answer = LegalAnswer(summary='Test response.', citations=['E1'])
    provider = SimpleNamespace(
        generate=AsyncMock(
            return_value=SimpleNamespace(
                content=answer.model_dump_json()
            )
        )
    )
    generator = LegalAnswerGenerator(provider)
    evidence = [
        LegalEvidence(
            citation_id='E1',
            chunk_id=1,
            content=(
                'Whoever causes hurt on grave and sudden provocation '
                'shall be punished.'
            ),
        )
    ]
    feedback = penalty_retry_feedback(claim_result(QUALIFIER))

    asyncio.run(
        generator.generate(
            user_query='A person hit me without provocation.',
            evidence=evidence,
            retry_mode=True,
            integrity_issue_codes=['contradictory_legal_qualifier'],
            claim_corrections=feedback,
        )
    )

    request = provider.generate.await_args.args[0]
    user_prompt = request.messages[-1].content

    assert 'provocation_condition_mismatch' in user_prompt
    assert 'contradictory_legal_qualifier' in user_prompt
    assert 'no provocation' in user_prompt
