import asyncio

from app.schemas.legal_evidence import LegalEvidence
from app.services.legal_answer_generator import (
    LegalAnswerGenerator,
)
from app.services.llm_factory import (
    get_llm_provider,
)


async def main():

    evidence = LegalEvidence(
        chunk_id=1,

        content=(
            "This is a controlled test of the "
            "retrieval-grounded answer pipeline."
        ),

        act_name=(
            "Bharatiya Nyaya Sanhita, 2023"
        ),

        act_short_name="BNS",

        version_label=(
            "BNS 2023 — Original"
        ),

        section_number="TEST",

        section_title=(
            "Controlled Grounding Test"
        ),

        source_name=(
            "BNS Gazette"
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

    provider = get_llm_provider()

    generator = LegalAnswerGenerator(
        provider
    )

    answer = await generator.generate(
        user_query=(
            "What does the supplied evidence say?"
        ),
        evidence=[evidence],
    )

    print("\n=== NYAYAAI GROUNDED ANSWER ===")

    print("\nSummary:")
    print(answer.summary)

    print("\nLegal Basis:")
    for item in answer.legal_basis:
        print("-", item)

    print("\nPossible Options:")
    for item in answer.possible_options:
        print("-", item)

    print("\nEvidence To Preserve:")
    for item in answer.evidence_to_preserve:
        print("-", item)

    print("\nNext Steps:")
    for item in answer.next_steps:
        print("-", item)

    print("\nCaveats:")
    for item in answer.caveats:
        print("-", item)

    print("\nCitations:")
    for item in answer.citations:
        print("-", item)


if __name__ == "__main__":
    asyncio.run(main())