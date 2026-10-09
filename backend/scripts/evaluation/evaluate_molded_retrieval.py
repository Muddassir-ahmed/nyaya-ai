from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from app.db.session import AsyncSessionLocal
from app.services.legal_evidence import build_legal_evidence
from app.services.legal_retrieval_orchestrator import (
    LegalRetrievalOrchestrator,
)
from scripts.evaluation.molded_query_dataset import (
    MOLDED_RETRIEVAL_DATASET,
)


async def evaluate(output_path: Path) -> int:
    orchestrator = LegalRetrievalOrchestrator()
    results: list[dict] = []

    async with AsyncSessionLocal() as db:
        for example in MOLDED_RETRIEVAL_DATASET:
            started = time.perf_counter()

            try:
                retrieval = await orchestrator.retrieve(
                    db=db,
                    query=example.query,
                    top_k=5,
                    candidate_k=20,
                )

                evidence = await build_legal_evidence(
                    db=db,
                    chunks=retrieval.chunks,
                )

                retrieved = [
                    {
                        "chunk_id": item.chunk_id,
                        "act_short_name": item.act_short_name,
                        "section_number": item.section_number,
                        "subsection_number": item.subsection_number,
                    }
                    for item in evidence
                ]

                expected = {
                    (
                        example.expected_act_short_name,
                        section,
                    )
                    for section in example.expected_section_numbers
                }

                observed = {
                    (
                        item.act_short_name,
                        item.section_number,
                    )
                    for item in evidence
                }

                passed = bool(
                    expected.intersection(observed)
                )

                error = None

            except Exception as exc:
                retrieval = None
                retrieved = []
                passed = False
                error = (
                    f"{type(exc).__name__}: {exc}"
                )

            elapsed = round(
                time.perf_counter() - started,
                2,
            )

            result = {
                "case_id": example.case_id,
                "category": example.category,
                "query": example.query,
                "expected": {
                    "act_short_name": (
                        example.expected_act_short_name
                    ),
                    "section_numbers": list(
                        example.expected_section_numbers
                    ),
                },
                "passed": passed,
                "elapsed_seconds": elapsed,
                "analysis": (
                    retrieval.analysis.model_dump(
                        mode="json"
                    )
                    if retrieval is not None
                    else None
                ),
                "retrieval_query": (
                    retrieval.retrieval_query
                    if retrieval is not None
                    else None
                ),
                "retrieval_queries": (
                    retrieval.retrieval_queries
                    if retrieval is not None
                    else []
                ),
                "retrieved": retrieved,
                "error": error,
            }

            results.append(result)

            print()
            print("=" * 78)
            print(
                example.case_id,
                "—",
                example.category,
            )
            print("=" * 78)
            print("Query:", example.query)
            print(
                "Expected:",
                example.expected_act_short_name,
                list(example.expected_section_numbers),
            )
            print(
                "Retrieved:",
                [
                    (
                        item["act_short_name"],
                        item["section_number"],
                    )
                    for item in retrieved
                ],
            )
            print("Passed:", passed)
            print("Elapsed:", elapsed, "seconds")

            if error:
                print("Error:", error)

    passed_count = sum(
        1
        for result in results
        if result["passed"]
    )
    failed = [
        result["case_id"]
        for result in results
        if not result["passed"]
    ]
    categories = Counter(
        result["category"]
        for result in results
        if result["passed"]
    )

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "case_count": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "failed_case_ids": failed,
        "passed_categories": dict(categories),
        "results": results,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 78)
    print("C-24Q MOLDED-QUERY RETRIEVAL SUMMARY")
    print("=" * 78)
    print("Cases:", len(results))
    print("Passed:", passed_count)
    print("Failed:", len(results) - passed_count)
    print("Failed cases:", failed or "none")
    print("Saved:", output_path)

    return 0 if not failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only NyayaAI molded-query retrieval gate."
        )
    )
    parser.add_argument(
        "--output",
        default="nyaya_c24q_molded_retrieval.json",
        help="JSON result path.",
    )
    args = parser.parse_args()

    return asyncio.run(
        evaluate(Path(args.output).resolve())
    )


if __name__ == "__main__":
    raise SystemExit(main())
