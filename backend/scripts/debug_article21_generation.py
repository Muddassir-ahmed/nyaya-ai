import asyncio
import json

from app.db.session import AsyncSessionLocal
from app.services.query_analyzer import (
    get_query_analyzer,
)
from app.services.legal_retrieval_orchestrator import (
    LegalRetrievalOrchestrator,
)
from app.services.legal_evidence import (
    build_legal_evidence,
)
from app.services.verified_evidence import (
    verify_evidence_list,
)
from app.services.legal_answer_generator import (
    LegalAnswerGenerator,
)
from app.services.llm_factory import (
    get_llm_provider,
)
from app.services.citation_validation import (
    GeneratedAnswerCitationValidator,
)
from app.services.claim_validator import (
    LegalClaimValidator,
)


QUERY = "What is the punishment for theft?"


async def main() -> None:
    analyzer = get_query_analyzer()
    analysis = analyzer.analyze(QUERY)

    retrieval = LegalRetrievalOrchestrator()

    async with AsyncSessionLocal() as db:
        result = await retrieval.retrieve(
            db=db,
            query=QUERY,
            top_k=5,
            candidate_k=20,
            analysis=analysis,
        )

        print()
        print("=" * 70)
        print("RETRIEVAL")
        print("=" * 70)

        print(
            "Exact reference:",
            result.exact_reference,
        )

        print(
            "Exact status:",
            result.exact_reference_status,
        )

        print(
            "Chunks:",
            len(result.chunks),
        )

        raw_evidence = await build_legal_evidence(
            db=db,
            chunks=result.chunks,
        )

        verified_items = verify_evidence_list(
            raw_evidence
        )

        verified_evidence = [
            item.evidence
            for item in verified_items
        ]

        print()
        print("=" * 70)
        print("VERIFIED EVIDENCE")
        print("=" * 70)

        for evidence in verified_evidence:
            print(
                json.dumps(
                    evidence.model_dump(
                        mode="json"
                    ),
                    indent=2,
                    ensure_ascii=False,
                )
            )

        generator = LegalAnswerGenerator(
            get_llm_provider()
        )

        generated = await generator.generate(
            user_query=QUERY,
            evidence=verified_evidence,
        )

        print()
        print("=" * 70)
        print("RAW PARSED LLM ANSWER")
        print("=" * 70)

        print(
            json.dumps(
                generated.model_dump(
                    mode="json"
                ),
                indent=2,
                ensure_ascii=False,
            )
        )

        print()
        print("=" * 70)
        print("CITATIONS EXACTLY AS GENERATED")
        print("=" * 70)

        print(
            repr(
                generated.citations
            )
        )

        for index, citation in enumerate(
            generated.citations,
            start=1,
        ):
            print(
                f"{index}: "
                f"{citation!r}"
            )

        citation_result = (
            GeneratedAnswerCitationValidator
            .validate(
                answer=generated,
                evidence=verified_evidence,
            )
        )

        claim_result = (
            LegalClaimValidator.validate(
                answer=generated,
                evidence=verified_evidence,
            )
        )

        print()
        print("=" * 70)
        print("VALIDATION")
        print("=" * 70)

        print(
            "Citation valid:",
            citation_result.is_valid,
        )

        print(
            "Citation completeness:",
            citation_result.citation_completeness,
        )

        print(
            "Valid citations:",
            citation_result.valid_citations,
        )

        print(
            "Invalid citations:",
            citation_result.invalid_citations,
        )

        print(
            "Citation reasons:",
            citation_result.validation_reasons,
        )

        print(
            "Claim grounding valid:",
            claim_result.is_valid,
        )

        print()
        print("=" * 70)
        print("CLAIM DETAILS")
        print("=" * 70)

        for index, item in enumerate(
            claim_result.claims,
            start=1,
        ):
            print()
            print(f"Claim {index}:")
            print("Text:", item.claim)
            print(
                "Support:",
                item.support_level.value,
            )
            print(
                "Citations:",
                item.citation_ids,
            )
            print(
                "Reason:",
                item.reason,
            )

        print()
        print(
            "Unsupported claims:",
            claim_result.unsupported_claims,
        )

        print(
            "Partially supported claims:",
            claim_result.partially_supported_claims,
        )


if __name__ == "__main__":
    asyncio.run(main())
