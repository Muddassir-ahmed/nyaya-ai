from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.answer_integrity import (
    AnswerIntegrityResult,
)
from app.schemas.authority import AuthorityResponse
from app.schemas.citation_validation import (
    CitationValidationResult,
)
from app.schemas.claim_validation import (
    ClaimValidationResult,
)
from app.schemas.emergency import EmergencyResponse
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.schemas.query_analysis import (
    LegalIntent,
    QueryAnalysis,
)
from app.services.answer_integrity import (
    LegalAnswerIntegrityValidator,
)
from app.services.authority_orchestrator import (
    AuthorityOrchestrator,
)
from app.services.citation_validation import (
    GeneratedAnswerCitationValidator,
)
from app.services.claim_validator import LegalClaimValidator
from app.services.penalty_retry import penalty_retry_feedback
from app.services.emergency_orchestrator import (
    EmergencyOrchestrator,
)
from app.services.legal_answer_generator import (
    LegalAnswerGenerator,
)
from app.services.legal_evidence import build_legal_evidence
from app.services.legal_retrieval_orchestrator import (
    LegalRetrievalOrchestrator,
)
from app.services.llm_factory import get_llm_provider
from app.services.query_analyzer import get_query_analyzer
from app.services.verified_evidence import verify_evidence_list


@dataclass
class QueryOrchestrationResult:
    route: str
    analysis: QueryAnalysis

    emergency_response: EmergencyResponse | None = None
    authority_response: AuthorityResponse | None = None
    legal_answer: LegalAnswer | None = None

    evidence: list[LegalEvidence] = field(default_factory=list)

    citation_validation: CitationValidationResult | None = None
    claim_validation: ClaimValidationResult | None = None
    answer_integrity: AnswerIntegrityResult | None = None
    retrieval_performed: bool = False
    routing_reason: str | None = None

    answer_blocked: bool = False
    safety_reason: str | None = None

    follow_up_question: str | None = None


class QueryOrchestrator:
    """
    Top-level NyayaAI query orchestrator.

    Responsibilities:

    1. Analyze the user's situation.
    2. Short-circuit emergencies before legal RAG.
    3. Route normal legal queries through legal retrieval.
    4. Build structured evidence.
    5. Reject evidence that fails provenance verification.
    6. Generate a grounded legal answer.
    7. Validate generated citations.
    8. Validate claim-level grounding.

    Emergency contact numbers never come from the LLM.
    """

    def __init__(
        self,
        emergency_orchestrator: EmergencyOrchestrator | None = None,
        authority_orchestrator: AuthorityOrchestrator | None = None,
        legal_retrieval_orchestrator: LegalRetrievalOrchestrator | None = None,
        legal_answer_generator: LegalAnswerGenerator | None = None,
    ):
        self.query_analyzer = get_query_analyzer()

        self.emergency_orchestrator = (
            emergency_orchestrator
            or EmergencyOrchestrator(query_analyzer=self.query_analyzer)
        )

        self.authority_orchestrator = (
            authority_orchestrator
            or AuthorityOrchestrator(query_analyzer=self.query_analyzer)
        )

        self.legal_retrieval_orchestrator = (
            legal_retrieval_orchestrator or LegalRetrievalOrchestrator()
        )

        self.legal_answer_generator = (
            legal_answer_generator
            or LegalAnswerGenerator(get_llm_provider())
        )

    @staticmethod
    def _apply_explicit_jurisdiction(
        analysis: QueryAnalysis,
        jurisdiction: str | None,
    ) -> QueryAnalysis:
        """
        Apply trusted caller-provided jurisdiction context.

        Explicit caller context takes precedence over jurisdiction
        detected from the query.
        """
        if jurisdiction is None:
            return analysis

        value = jurisdiction.strip()

        if not value:
            return analysis

        remaining_missing = [
            item
            for item in analysis.missing_information
            if item != "state_or_jurisdiction"
        ]

        return analysis.model_copy(
            update={
                "jurisdiction": value,
                "requires_follow_up": bool(remaining_missing),
                "missing_information": remaining_missing,
            }
        )

    @staticmethod
    def _build_follow_up_question(
        analysis: QueryAnalysis,
    ) -> str:
        """
        Build a deterministic follow-up question from the
        analyzer's missing-information signals.
        """
        if "state_or_jurisdiction" in analysis.missing_information:
            return (
                "Which Indian state or union territory "
                "is this situation in?"
            )

        return (
            "What additional information can you provide "
            "so I can route this accurately?"
        )

    @staticmethod
    def _build_exact_reference_answer(
        reference: str,
        status: str,
    ) -> LegalAnswer:
        """
        Build deterministic answers for exact
        constitutional references that must not
        go through the LLM.

        Supported statuses:
        - omitted
        - not_found
        """
        if status == "omitted":
            return LegalAnswer(
                summary=(
                    f"{reference} is marked as omitted "
                    "in the Constitution version "
                    "currently loaded and verified "
                    "by NyayaAI."
                ),
                legal_basis=[],
                possible_options=[],
                evidence_to_preserve=[],
                next_steps=[],
                caveats=[
                    (
                        "NyayaAI does not generate or "
                        "reconstruct substantive text "
                        "for an omitted constitutional "
                        "provision."
                    ),
                    (
                        "This response comes from the "
                        "structured Constitution record "
                        "rather than semantic retrieval "
                        "or LLM generation."
                    ),
                ],
                citations=[],
            )

        if status == "not_found":
            return LegalAnswer(
                summary=(
                    f"{reference} was not found in the "
                    "Constitution version currently "
                    "loaded and verified by NyayaAI."
                ),
                legal_basis=[],
                possible_options=[],
                evidence_to_preserve=[],
                next_steps=[],
                caveats=[
                    (
                        "NyayaAI will not substitute a "
                        "different Article or infer a "
                        "nearby provision when an exact "
                        "Article reference cannot be "
                        "resolved."
                    ),
                ],
                citations=[],
            )

        raise ValueError(f"Unsupported exact-reference status: {status}")

    async def handle(
        self,
        db: AsyncSession,
        query: str,
        jurisdiction: str | None = None,
        top_k: int = 5,
        candidate_k: int = 20,
        effective_date: date | None = None,
    ) -> QueryOrchestrationResult:
        """
        Process one NyayaAI user query.

        Emergency queries are intercepted before any legal retrieval
        or LLM-based legal-answer generation occurs.
        """
        analysis = self.query_analyzer.analyze(query)

        analysis = self._apply_explicit_jurisdiction(
            analysis=analysis,
            jurisdiction=jurisdiction,
        )

        # -----------------------------------------------------
        # 1. Emergency short-circuit.
        # -----------------------------------------------------

        if analysis.intent == LegalIntent.EMERGENCY:
            emergency_response = await self.emergency_orchestrator.handle(
                db=db,
                query=query,
                jurisdiction=jurisdiction,
            )

            return QueryOrchestrationResult(
                route="emergency",
                analysis=analysis,
                emergency_response=emergency_response,
                retrieval_performed=False,
                routing_reason=(
                    "Emergency query routed to the "
                    "verified safety/emergency pipeline."
                ),
            )

        # -----------------------------------------------------
        # 2. Missing information / follow-up routing.
        # -----------------------------------------------------

        if analysis.requires_follow_up:
            return QueryOrchestrationResult(
                route="follow_up",
                analysis=analysis,
                retrieval_performed=False,
                routing_reason=(
                    "Additional jurisdiction or contextual "
                    "information is required before routing."
                ),
                follow_up_question=self._build_follow_up_question(analysis),
            )

        # -----------------------------------------------------
        # 3. Structured authority routing.
        # -----------------------------------------------------

        if analysis.intent == LegalIntent.AUTHORITY_LOOKUP:
            authority_response = await self.authority_orchestrator.handle(
                db=db,
                query=query,
                jurisdiction=jurisdiction,
                analysis=analysis,
            )

            return QueryOrchestrationResult(
                route="authority",
                analysis=analysis,
                authority_response=authority_response,
                retrieval_performed=False,
                routing_reason=(
                    "Authority lookup routed to the "
                    "verified structured authority directory."
                ),
            )

        # -----------------------------------------------------
        # 4. Civic-service routing.
        # -----------------------------------------------------

        if analysis.intent == LegalIntent.GENERAL_CIVIC:
            return QueryOrchestrationResult(
                route="civic",
                analysis=analysis,
                retrieval_performed=False,
                routing_reason=(
                    "General civic query routed to the "
                    "civic service pipeline."
                ),
            )

        # -----------------------------------------------------
        # 5. Out-of-scope routing.
        # -----------------------------------------------------

        if analysis.intent == LegalIntent.OUT_OF_SCOPE:
            return QueryOrchestrationResult(
                route="out_of_scope",
                analysis=analysis,
                retrieval_performed=False,
                routing_reason=(
                    "Query is outside the currently "
                    "supported legal/civic scope."
                ),
            )

        # -----------------------------------------------------
        # 6. Legal retrieval routing.
        # -----------------------------------------------------

        retrieval_result = await self.legal_retrieval_orchestrator.retrieve(
            db=db,
            query=query,
            top_k=top_k,
            candidate_k=candidate_k,
            effective_date=effective_date,
            analysis=analysis,
        )

        # -----------------------------------------------------
        # 7. Deterministic exact-reference results.
        #
        # Omitted or nonexistent constitutional Articles
        # must never enter:
        #
        #   semantic fallback
        #   evidence generation
        #   LLM generation
        #
        # Their status has already been determined from the
        # structured authoritative Constitution hierarchy.
        # -----------------------------------------------------

        if retrieval_result.exact_reference_status in {"omitted", "not_found"}:
            reference = retrieval_result.exact_reference

            if reference is None:
                raise RuntimeError(
                    "Exact-reference status exists without an exact reference."
                )

            legal_answer = self._build_exact_reference_answer(
                reference=reference,
                status=retrieval_result.exact_reference_status,
            )

            return QueryOrchestrationResult(
                route="legal",
                analysis=retrieval_result.analysis,
                legal_answer=legal_answer,
                evidence=[],
                citation_validation=None,
                claim_validation=None,
                retrieval_performed=True,
                routing_reason=retrieval_result.retrieval_reason,
                answer_blocked=False,
                safety_reason=None,
            )

        # -----------------------------------------------------
        # 8. Non-RAG or follow-up-required query.
        # -----------------------------------------------------

        if not retrieval_result.retrieval_performed:
            result_analysis = retrieval_result.analysis

            if result_analysis.requires_follow_up:
                return QueryOrchestrationResult(
                    route="follow_up",
                    analysis=result_analysis,
                    retrieval_performed=False,
                    routing_reason=retrieval_result.retrieval_reason,
                    follow_up_question=self._build_follow_up_question(
                        result_analysis
                    ),
                )

            if result_analysis.intent == LegalIntent.AUTHORITY_LOOKUP:
                route = "authority"
            elif result_analysis.intent == LegalIntent.GENERAL_CIVIC:
                route = "civic"
            elif result_analysis.intent == LegalIntent.OUT_OF_SCOPE:
                route = "out_of_scope"
            else:
                route = "non_rag"

            return QueryOrchestrationResult(
                route=route,
                analysis=result_analysis,
                retrieval_performed=False,
                routing_reason=retrieval_result.retrieval_reason,
            )

        # -----------------------------------------------------
        # 9. Convert retrieved chunks to structured evidence.
        # -----------------------------------------------------

        raw_evidence = await build_legal_evidence(
            db=db,
            chunks=retrieval_result.chunks,
        )

        # -----------------------------------------------------
        # 10. Verify provenance and assign E1, E2, ...
        # -----------------------------------------------------

        verified_items = verify_evidence_list(raw_evidence)

        verified_evidence = [item.evidence for item in verified_items]

        # -----------------------------------------------------
        # 11. No verified evidence = safe refusal.
        #
        # LegalAnswerGenerator already contains deterministic
        # insufficient-evidence behavior and does not call the
        # LLM when evidence is empty.
        # -----------------------------------------------------

        legal_answer = await self.legal_answer_generator.generate(
            user_query=query,
            evidence=verified_evidence,
        )

        if not verified_evidence:
            return QueryOrchestrationResult(
                route="legal",
                analysis=retrieval_result.analysis,
                legal_answer=legal_answer,
                evidence=[],
                retrieval_performed=True,
                routing_reason=(
                    "Legal retrieval completed, but no "
                    "evidence passed provenance verification."
                ),
            )

        # -----------------------------------------------------
        # 12. Validate generated citation IDs.
        # -----------------------------------------------------

        citation_validation = GeneratedAnswerCitationValidator.validate(
            answer=legal_answer,
            evidence=verified_evidence,
        )

        # -----------------------------------------------------
        # 13. Validate legal claims against evidence.
        # -----------------------------------------------------

        claim_validation = LegalClaimValidator.validate(
            answer=legal_answer,
            evidence=verified_evidence,
            user_query=query,
        )

        # -----------------------------------------------------
        # 14. Validate answer-level legal integrity.
        #
        # This catches issues that lexical claim grounding
        # alone cannot safely detect, such as incomplete
        # legal qualifiers, altered numeric conditions, or
        # unrequested special/aggravated provisions.
        # -----------------------------------------------------

        answer_integrity = LegalAnswerIntegrityValidator.validate(
            user_query=query,
            answer=legal_answer,
            evidence=verified_evidence,
        )

        # -----------------------------------------------------
        # 15. Controlled answer-integrity retry.
        #
        # Retry only when:
        # - citations are valid;
        # - claim grounding is valid;
        # - answer-integrity alone failed.
        #
        # Retrieval and evidence are NOT repeated.
        # Only one regeneration attempt is allowed.
        # -----------------------------------------------------

        citation_failed = not citation_validation.is_valid
        claim_failed = not claim_validation.is_valid
        integrity_failed = not answer_integrity.is_valid

        claim_corrections = penalty_retry_feedback(claim_validation)
        if not citation_failed and (
            (not claim_failed and integrity_failed)
            or bool(claim_corrections)
        ):
            integrity_issue_codes = sorted(
                {
                    issue.code
                    for issue in answer_integrity.issues
                }
            )

            omitted_qualified_rule_counts: dict[
                str,
                int,
            ] = {}

            for issue in answer_integrity.issues:
                if (
                    issue.code == "omitted_qualified_rule"
                    and issue.citation_id
                ):
                    omitted_qualified_rule_counts[
                        issue.citation_id
                    ] = (
                        omitted_qualified_rule_counts.get(
                            issue.citation_id,
                            0,
                        )
                        + 1
                    )

            legal_answer = await self.legal_answer_generator.generate(
                user_query=query,
                evidence=verified_evidence,
                retry_mode=True,
                integrity_issue_codes=(
                    integrity_issue_codes
                ),
                omitted_qualified_rule_counts=(
                    omitted_qualified_rule_counts
                    or None
                ),
                **(
                    {"claim_corrections": claim_corrections}
                    if claim_corrections else {}
                ),
            )

            # Every safety gate must run again against
            # the regenerated answer.
            citation_validation = GeneratedAnswerCitationValidator.validate(
                answer=legal_answer,
                evidence=verified_evidence,
            )

            claim_validation = LegalClaimValidator.validate(
                answer=legal_answer,
                evidence=verified_evidence,
                user_query=query,
            )

            answer_integrity = LegalAnswerIntegrityValidator.validate(
                user_query=query,
                answer=legal_answer,
                evidence=verified_evidence,
            )

            citation_failed = not citation_validation.is_valid
            claim_failed = not claim_validation.is_valid
            integrity_failed = not answer_integrity.is_valid

        # -----------------------------------------------------
        # 16. Final legal-answer safety gate.
        # -----------------------------------------------------

        if citation_failed or claim_failed or integrity_failed:
            reasons = []

            if citation_failed:
                reasons.append(
                    "generated citations could not be fully verified"
                )

            if claim_failed:
                reasons.append(
                    "one or more generated legal claims were not "
                    "sufficiently supported by verified evidence"
                )

            if integrity_failed:
                reasons.append(
                    "the generated legal answer failed "
                    "answer-integrity checks"
                )

            safety_reason = "; ".join(reasons)

            safe_answer = LegalAnswer(
                summary=(
                    "I cannot safely provide the generated legal "
                    "answer because it did not pass NyayaAI's "
                    "evidence-grounding checks."
                ),
                legal_basis=[],
                possible_options=[],
                evidence_to_preserve=[],
                next_steps=[],
                caveats=[
                    (
                        "The generated response was blocked because "
                        "its legal claims or citations could not be "
                        "sufficiently verified against the available "
                        "legal evidence."
                    ),
                    (
                        "Try providing more details or consult an "
                        "appropriate qualified professional if the "
                        "matter requires legal advice."
                    ),
                ],
                citations=[],
            )

            return QueryOrchestrationResult(
                route="legal",
                analysis=retrieval_result.analysis,
                legal_answer=safe_answer,
                evidence=verified_evidence,
                citation_validation=citation_validation,
                claim_validation=claim_validation,
                answer_integrity=answer_integrity,
                retrieval_performed=True,
                routing_reason=None,
                answer_blocked=True,
                safety_reason=safety_reason,
            )

        # -----------------------------------------------------
        # 17. All safety checks passed.
        # -----------------------------------------------------

        return QueryOrchestrationResult(
            route="legal",
            analysis=retrieval_result.analysis,
            legal_answer=legal_answer,
            evidence=verified_evidence,
            citation_validation=citation_validation,
            claim_validation=claim_validation,
            answer_integrity=answer_integrity,
            retrieval_performed=True,
            routing_reason=None,
            answer_blocked=False,
            safety_reason=None,
        )


def get_query_orchestrator() -> QueryOrchestrator:
    return QueryOrchestrator()
