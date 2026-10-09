import asyncio
from dataclasses import dataclass

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.legal_version import LegalVersion
from app.models.section import Section
from app.services.hybrid_retrieval import hybrid_search_legal_chunks

from scripts.evaluation.retrieval_dataset import RETRIEVAL_DATASET


@dataclass
class EvaluationResult:
    query: str
    expected_sections: set[str]
    retrieved_sections: list[str]


async def get_expected_section_numbers(
    db,
    section_numbers: tuple[str, ...],
) -> set[str]:
    result = await db.execute(
        select(Section.section_number)
        .join(
            LegalVersion,
            Section.version_id == LegalVersion.id,
        )
        .where(
            LegalVersion.status == "active",
            Section.section_number.in_(section_numbers),
        )
    )

    return set(result.scalars().all())


async def get_section_number(
    db,
    section_id: int,
) -> str | None:
    result = await db.execute(
        select(Section.section_number)
        .where(Section.id == section_id)
    )

    return result.scalar_one_or_none()


def hit_at_k(
    expected: set[str],
    retrieved: list[str],
    k: int,
) -> float:
    return float(
        bool(expected.intersection(retrieved[:k]))
    )


def recall_at_k(
    expected: set[str],
    retrieved: list[str],
    k: int,
) -> float:
    if not expected:
        return 0.0

    retrieved_at_k = set(retrieved[:k])

    relevant_retrieved = (
        expected.intersection(retrieved_at_k)
    )

    return len(relevant_retrieved) / len(expected)


def reciprocal_rank(
    expected: set[str],
    retrieved: list[str],
) -> float:
    for rank, section_number in enumerate(
        retrieved,
        start=1,
    ):
        if section_number in expected:
            return 1.0 / rank

    return 0.0


async def evaluate() -> None:
    evaluation_results: list[EvaluationResult] = []

    top_k = 5
    candidate_k = 20

    async with AsyncSessionLocal() as db:

        for example in RETRIEVAL_DATASET:

            expected_sections = (
                await get_expected_section_numbers(
                    db,
                    example.expected_section_numbers,
                )
            )

            if not expected_sections:
                print(
                    f"WARNING: No expected sections found "
                    f"for query: {example.query}"
                )
                continue

            chunks = await hybrid_search_legal_chunks(
                db=db,
                query=example.query,
                top_k=top_k,
                candidate_k=candidate_k,
            )

            retrieved_sections = []

            for chunk in chunks:

                if chunk.section_id is None:
                    continue

                section_number = await get_section_number(
                    db,
                    chunk.section_id,
                )

                if section_number is None:
                    continue

                # Avoid duplicate chunks from the same section.
                if section_number not in retrieved_sections:
                    retrieved_sections.append(
                        section_number
                    )

            evaluation_results.append(
                EvaluationResult(
                    query=example.query,
                    expected_sections=expected_sections,
                    retrieved_sections=retrieved_sections,
                )
            )

    if not evaluation_results:
        print("No evaluation results available.")
        return

    hit_scores = {
        1: [],
        3: [],
        5: [],
    }

    recall_scores = {
        1: [],
        3: [],
        5: [],
    }

    mrr_scores = []

    print()
    print("=" * 80)
    print("NYAYAAI — RETRIEVAL EVALUATION")
    print("=" * 80)

    print(
        f"\nDataset size: "
        f"{len(evaluation_results)} queries"
    )

    print(f"Top K: {top_k}")
    print(f"Candidate K: {candidate_k}")

    print()

    for index, result in enumerate(
        evaluation_results,
        start=1,
    ):
        print("-" * 80)
        print(f"Query {index}: {result.query}")

        print(
            f"Expected sections: "
            f"{sorted(result.expected_sections)}"
        )

        print(
            f"Retrieved sections: "
            f"{result.retrieved_sections}"
        )

        query_mrr = reciprocal_rank(
            result.expected_sections,
            result.retrieved_sections,
        )

        print(
            f"MRR contribution: "
            f"{query_mrr:.4f}"
        )

        for k in (1, 3, 5):

            hit_score = hit_at_k(
                result.expected_sections,
                result.retrieved_sections,
                k,
            )

            recall_score = recall_at_k(
                result.expected_sections,
                result.retrieved_sections,
                k,
            )

            hit_scores[k].append(hit_score)
            recall_scores[k].append(recall_score)

        mrr_scores.append(query_mrr)

    total_queries = len(evaluation_results)

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\nHit Rate")
    print("-" * 40)

    for k in (1, 3, 5):
        score = (
            sum(hit_scores[k])
            / total_queries
        )

        print(
            f"Hit@{k}: "
            f"{score:.2%}"
        )

    print("\nRecall")
    print("-" * 40)

    for k in (1, 3, 5):
        score = (
            sum(recall_scores[k])
            / total_queries
        )

        print(
            f"Recall@{k}: "
            f"{score:.2%}"
        )

    mean_mrr = (
        sum(mrr_scores)
        / total_queries
    )

    print("\nMean Reciprocal Rank")
    print("-" * 40)

    print(
        f"MRR: "
        f"{mean_mrr:.4f}"
    )

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(evaluate())