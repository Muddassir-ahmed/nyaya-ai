from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from app.db.session import AsyncSessionLocal
from app.services.query_orchestrator import get_query_orchestrator


@dataclass(frozen=True)
class LiveCase:
    case_id: str
    query: str
    expected_act: str
    expected_sections: tuple[str, ...]
    forbidden_legal_basis_text: tuple[str, ...] = ()


CASES = [
    LiveCase(
        case_id="LIVE-MOB-LYNCHING",
        query=(
            "What is the provision for mob lynching under the BNS, "
            "and what is the punishment?"
        ),
        expected_act="BNS",
        expected_sections=("103",),
    ),
    LiveCase(
        case_id="LIVE-SNATCHING-SCENARIO",
        query=(
            "A rider suddenly grabbed a phone from someone's hand and "
            "sped away. Which BNS offence describes this and what is the "
            "punishment?"
        ),
        expected_act="BNS",
        expected_sections=("304",),
    ),
    LiveCase(
        case_id="LIVE-TERRORIST-ACT",
        query=(
            "How does the BNS define a terrorist act and what punishment "
            "does the provision state?"
        ),
        expected_act="BNS",
        expected_sections=("113",),
    ),
    LiveCase(
        case_id="LIVE-UNPROVOKED-HITTING",
        query=(
            "A person intentionally hit me without any provocation. I am "
            "safe now. Which BNS provision may apply?"
        ),
        expected_act="BNS",
        expected_sections=("131",),
        forbidden_legal_basis_text=("section 122",),
    ),
    LiveCase(
        case_id="LIVE-CONSTITUTION-LIBERTY",
        query=(
            "Which constitutional protection says that a person cannot "
            "be deprived of life or personal liberty except according to "
            "procedure established by law?"
        ),
        expected_act="COI",
        expected_sections=("21",),
    ),
]


def validation_value(value) -> bool | None:
    return (
        value.is_valid
        if value is not None
        else None
    )


async def run(output_path: Path) -> int:
    orchestrator = get_query_orchestrator()
    results: list[dict] = []

    async with AsyncSessionLocal() as db:
        for case in CASES:
            started = time.perf_counter()
            error = None

            try:
                response = await orchestrator.handle(
                    db=db,
                    query=case.query,
                )

                evidence_pairs = [
                    (
                        item.act_short_name,
                        item.section_number,
                    )
                    for item in response.evidence
                ]

                expected_evidence = any(
                    act == case.expected_act
                    and section in case.expected_sections
                    for act, section in evidence_pairs
                )

                legal_basis = (
                    response.legal_answer.legal_basis
                    if response.legal_answer
                    else []
                )
                basis_text = " ".join(
                    legal_basis
                ).casefold()

                forbidden_absent = all(
                    text.casefold() not in basis_text
                    for text in case.forbidden_legal_basis_text
                )

                checks = {
                    "legal_route": response.route == "legal",
                    "retrieval_performed": (
                        response.retrieval_performed is True
                    ),
                    "expected_evidence": expected_evidence,
                    "answer_not_blocked": (
                        response.answer_blocked is False
                    ),
                    "citation_validation": (
                        validation_value(
                            response.citation_validation
                        )
                        is True
                    ),
                    "claim_validation": (
                        validation_value(
                            response.claim_validation
                        )
                        is True
                    ),
                    "integrity_validation": (
                        validation_value(
                            response.answer_integrity
                        )
                        is True
                    ),
                    "forbidden_legal_basis_absent": forbidden_absent,
                }

                passed = all(checks.values())

                answer = (
                    response.legal_answer.model_dump(
                        mode="json"
                    )
                    if response.legal_answer
                    else None
                )

                analysis = response.analysis.model_dump(
                    mode="json"
                )

            except Exception as exc:
                evidence_pairs = []
                checks = {}
                answer = None
                analysis = None
                passed = False
                error = f"{type(exc).__name__}: {exc}"

            elapsed = round(
                time.perf_counter() - started,
                2,
            )

            result = {
                "case_id": case.case_id,
                "query": case.query,
                "expected_act": case.expected_act,
                "expected_sections": list(
                    case.expected_sections
                ),
                "passed": passed,
                "checks": checks,
                "elapsed_seconds": elapsed,
                "analysis": analysis,
                "evidence": evidence_pairs,
                "answer": answer,
                "error": error,
            }
            results.append(result)

            print()
            print("=" * 78)
            print(case.case_id)
            print("=" * 78)
            print("Query:", case.query)
            print("Evidence:", evidence_pairs)
            print("Checks:", checks)
            print("Passed:", passed)
            print("Elapsed:", elapsed, "seconds")

            if error:
                print("Error:", error)

    failed = [
        item["case_id"]
        for item in results
        if not item["passed"]
    ]

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "case_count": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "failed_case_ids": failed,
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
    print("C-24Q LIVE ANSWER SUMMARY")
    print("=" * 78)
    print("Cases:", len(results))
    print("Passed:", len(results) - len(failed))
    print("Failed:", len(failed))
    print("Failed cases:", failed or "none")
    print("Saved:", output_path)

    return 0 if not failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only NyayaAI C-24Q live answer gate."
        )
    )
    parser.add_argument(
        "--output",
        default="nyaya_c24q_live_answers.json",
        help="JSON result path.",
    )
    args = parser.parse_args()

    return asyncio.run(
        run(Path(args.output).resolve())
    )


if __name__ == "__main__":
    raise SystemExit(main())
