from copy import deepcopy
from app.services.penalty_retry import build_penalty_retry_prompt

from pydantic import ValidationError

from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.schemas.llm import LLMMessage, LLMRequest
from app.services.legal_prompt import (
    SYSTEM_PROMPT,
    build_grounded_prompt,
)
from app.services.llm_provider import LLMProvider


class LegalAnswerGenerator:

    def __init__(
        self,
        provider: LLMProvider,
    ):
        self.provider = provider

    @staticmethod
    def _build_response_schema(
        evidence: list[LegalEvidence],
    ) -> dict:
        """
        Build the structured-output schema used
        for legal-answer generation.

        The base schema comes from LegalAnswer.

        For grounded generation we strengthen it:

        - all response fields are required;
        - unknown top-level fields are forbidden;
        - citations can only contain evidence IDs
          actually supplied to the model.
        """

        schema = deepcopy(
            LegalAnswer.model_json_schema()
        )

        properties = schema.get(
            "properties",
            {},
        )

        # Ollama should return every LegalAnswer
        # field explicitly, even fields whose
        # value is an empty list.
        schema["required"] = list(
            properties.keys()
        )

        schema["additionalProperties"] = False

        valid_citation_ids = [
            evidence_item.citation_id
            for evidence_item in evidence
            if evidence_item.citation_id
        ]

        citations_schema = properties.get(
            "citations"
        )

        if (
            citations_schema is not None
            and valid_citation_ids
        ):
            citations_schema["items"] = {
                "type": "string",
                "enum": valid_citation_ids,
            }

            citations_schema["minItems"] = 1

            citations_schema[
                "uniqueItems"
            ] = True

        return schema

    async def generate(
        self,
        user_query: str,
        evidence: list[LegalEvidence],
        retry_mode: bool = False,
        integrity_issue_codes: list[str] | None = None,
        omitted_qualified_rule_counts: dict[str, int] | None = None,
        claim_corrections: list[dict[str, str]] | None = None,
    ) -> LegalAnswer:

        if not evidence:
            return LegalAnswer(
                summary=(
                    "I do not have enough verified "
                    "legal evidence to answer this question."
                ),
                caveats=[
                    (
                        "The available legal evidence "
                        "is insufficient."
                    )
                ],
            )

        response_schema = (
            self._build_response_schema(
                evidence
            )
        )

        prompt = build_grounded_prompt(
            user_query=user_query,
            evidence=evidence,
            response_schema=response_schema,
        )

        if retry_mode:
            prompt = (
                prompt
                + """

CORRECTION RETRY:

The previous generated draft failed NyayaAI's
answer-integrity validation.

Generate the answer again from the SAME verified
legal evidence.

Do not rely on or reproduce the previous draft.

Re-check every rule in the verified evidence before
returning the answer.

In particular:

1. Do not omit any material rule that is directly
   relevant to the user's question.

2. Preserve every material condition attached to a
   qualified consequence.

3. Preserve conjunctions. If A + B + C are required,
   do not return A + B.

4. Do not alter monetary amounts, durations, numeric
   thresholds, conviction counts, or other conditions.

5. State each qualified rule once and completely.

6. For a broad punishment question, check the evidence
   for:
   - the general punishment;
   - repeat or subsequent-conviction punishment;
   - provisos, exceptions, thresholds, or special cases.

7. Do not add anything that is not supported by the
   verified evidence.

This is the only correction attempt. Perform a full
completeness check before returning the JSON object.
"""
            )

            issue_codes = sorted(
                set(
                    integrity_issue_codes
                    or []
                )
            )

            if issue_codes:
                prompt += (
                    "\n\n"
                    "AUTOMATED INTEGRITY FEEDBACK:\n"
                    "Detected validation categories:\n"
                )

                for code in issue_codes:
                    prompt += f"- {code}\n"

                if "unrequested_special_rule" in issue_codes:
                    prompt += """
TARGETED CORRECTION FOR unrequested_special_rule:

The previous draft included separate special or aggravated offences
whose distinctive circumstances were not supplied in the question.

Rebuild the answer around the provision directly answering the question.
Exclude those unrelated special offences from summary, legal_basis,
caveats, every other field, and citations. Introducing them with "if"
does not make them relevant to a broad question.

Keep the main provision's general punishment, repeat-conviction rules,
and material provisos, with all conditions intact. Do not drop those
rules merely because a broad question does not specify their conditions.

Do not merge different provisions' conditions or punishments.
"""


                if "omitted_qualified_rule" in issue_codes:
                    prompt += """
TARGETED CORRECTION FOR omitted_qualified_rule:

At least one material qualified legal consequence from the verified
controlling evidence was omitted from the previous draft.

Re-read the complete controlling evidence and identify every distinct qualified legal consequence
that is material to the user's question.

Treat each separate qualified consequence as a checklist item.

For every checklist item:

- identify the consequence;
- identify every condition attached to it;
- preserve all conjunctions and qualifiers;
- preserve numeric and temporal qualifiers;
- keep distinct rules separate.

The final answer must account for every material checklist item
that is relevant to the user's question.

If the controlling evidence contains multiple distinct qualified consequences,
include each one with all of its attached conditions.

Do not invent or infer a rule that is absent from the verified evidence.

For a broad legal consequence or punishment question,
do not exclude a distinct qualified consequence merely
because the user's question does not mention its conditions.

If the controlling evidence explicitly contains multiple
consequence rules, including provisos, exceptions, enhanced
rules, reduced rules, alternative consequences, or special
cases, the answer must account for each distinct consequence
and state the conditions attached to it.

Absence of those conditions from a broad user question is not
a reason to omit the rule. Do not assume the conditions are
satisfied; explain them as conditions.
"""

            if (
                "omitted_qualified_rule"
                in issue_codes
                and omitted_qualified_rule_counts
            ):
                prompt += """

STRUCTURED COMPLETENESS TARGETS:

"""

                for (
                    citation_id,
                    omitted_count,
                ) in sorted(
                    omitted_qualified_rule_counts.items()
                ):
                    prompt += (
                        f"- {citation_id} has "
                        f"{omitted_count} omitted qualified "
                        "penalty/consequence rule"
                        f"{'s' if omitted_count != 1 else ''} "
                        "that must be added to the corrected answer.\n"
                    )

                prompt += """

These counts refer to rules detected as missing from the
previous draft. They are NOT counts of all rules in the
evidence.

Use only the verified evidence to identify the missing rules.

Do not invent rules to satisfy the count.

Do not assume that the conditions of a qualified rule are true.
State the rule together with all of its attached conditions.

Before returning the JSON object, verify that the corrected
answer accounts for every omitted rule indicated above.
"""

            if "contradictory_legal_qualifier" in issue_codes:
                prompt += """

TARGETED CORRECTION FOR contradictory_legal_qualifier:

The previous draft applied a legal provision whose material factual
condition contradicted the user's stated facts or the cited evidence.

Re-check polarity words such as with, without, present, absent, on,
otherwise than, and not. Do not apply a provision requiring grave and
sudden provocation when the question states that there was no provocation,
or vice versa.

Use only a supplied provision whose triggering conditions match the
stated facts. Keep that provision's own consequence attached to it.
If no supplied evidence matches, state that the available evidence is
insufficient rather than forcing a provision to apply.
"""
        if retry_mode and claim_corrections:
            prompt += build_penalty_retry_prompt(claim_corrections)

        request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=SYSTEM_PROMPT,
                ),
                LLMMessage(
                    role="user",
                    content=prompt,
                ),
            ],

            # Structured generation benefits from
            # deterministic sampling.
            temperature=0.0,

            max_tokens=1200,

            response_schema=response_schema,
        )

        response = await self.provider.generate(
            request
        )

        return self._parse_response(
            response.content
        )

    @staticmethod
    def _parse_response(
        content: str,
    ) -> LegalAnswer:

        cleaned = content.strip()

        # Defensive compatibility for providers
        # that still wrap JSON in Markdown.
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if (
                lines
                and lines[0].startswith("```")
            ):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            cleaned = "\n".join(
                lines
            ).strip()

        try:
            return (
                LegalAnswer.model_validate_json(
                    cleaned
                )
            )

        except ValidationError:
            # Safe fallback:
            #
            # Do not attempt to regex-extract
            # claims or citations from arbitrary
            # malformed model output.
            #
            # The orchestration safety layer will
            # reject this because citations are
            # intentionally empty.
            return LegalAnswer(
                summary=cleaned,
                caveats=[
                    (
                        "The model did not return "
                        "the expected structured format."
                    )
                ],
            )
