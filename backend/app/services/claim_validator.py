import re
from difflib import SequenceMatcher

from app.schemas.claim_validation import (
    ClaimSupportLevel,
    ClaimValidation,
    ClaimValidationResult,
)
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.penalty_grounding import penalty_contradiction
from app.services.legal_qualifier_grounding import (
    PROVOCATION_CONDITION_MISMATCH_REASON,
    provocation_condition_mismatch,
)


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "may",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
}


NEGATION_WORDS = {
    "not",
    "no",
    "never",
    "without",
    "cannot",
    "can't",
    "doesn't",
    "isn't",
    "aren't",
    "nothing",
}


NEGATION_PATTERN = re.compile(
    r"\b("
    r"not|no|never|without|cannot|can't|"
    r"doesn't|does\s+not|do\s+not|did\s+not|"
    r"isn't|is\s+not|aren't|are\s+not|"
    r"wasn't|was\s+not|weren't|were\s+not|"
    r"nothing"
    r")\b",
    flags=re.IGNORECASE,
)


EXPLICIT_ABSENCE_PATTERNS = (
    re.compile(
        r"\b(?P<subject>[^,.;]{1,80}?)"
        r"\s+(?:is|are)\s+not\s+"
        r"(?:explicitly\s+)?"
        r"(?:mentioned|stated|included|present)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:does|do)\s+not\s+"
        r"(?:explicitly\s+)?"
        r"(?:mention|state|include)\s+"
        r"(?P<subject>[^,.;]{1,80})",
        flags=re.IGNORECASE,
    ),
)

SECTION_REFERENCE_PATTERN = re.compile(
    r"\bsection\s+"
    r"(?P<section>\d+[A-Za-z]?(?:-[A-Za-z0-9]+)?)"
    r"(?:"
    r"\s*(?:sub-?section\s*)?"
    r"(?P<subsection>\((?!\s*E\d+\s*\))\s*[^()]{1,20}\s*\))"
    r")?",
    flags=re.IGNORECASE,
)


ABSENCE_GENERIC_WORDS = {
    "word",
    "words",
    "term",
    "terms",
    "concept",
    "concepts",
    "principle",
    "principles",
}


class LegalClaimValidator:
    @staticmethod
    def _tokenize(
        text: str,
    ) -> set[str]:
        tokens = {
            word.lower().strip(
                ".,!?;:()[]{}\"'"
            )
            for word in text.split()
        }

        return {
            token
            for token in tokens
            if (
                len(token) >= 3
                and token not in STOPWORDS
            )
        }

    @classmethod
    def _evidence_grounding_text(
        cls,
        evidence: LegalEvidence,
    ) -> str:
        """
        Build the complete deterministic text representation
        used for claim grounding.

        Legal claims may correctly refer to verified structured
        citation metadata such as the Act, section, subsection,
        or clause even when those identifiers are not repeated
        verbatim inside the chunk body.
        """

        section_label = None

        if evidence.section_number:
            section_label = (
                f"Section "
                f"{evidence.section_number}"
            )

        subsection_label = None

        if evidence.subsection_number:
            subsection_label = (
                f"Subsection "
                f"{evidence.subsection_number}"
            )

        clause_label = None

        if evidence.clause_number:
            clause_label = (
                f"Clause "
                f"{evidence.clause_number}"
            )

        compact_reference = None

        if evidence.section_number:
            compact_reference = (
                f"{evidence.section_number}"
                f"{evidence.subsection_number or ''}"
                f"{evidence.clause_number or ''}"
            )

        metadata_parts = [
            evidence.content,
            evidence.act_name,
            evidence.act_short_name,
            evidence.version_label,
            section_label,
            evidence.section_title,
            subsection_label,
            clause_label,
            compact_reference,
        ]

        return " ".join(
            str(part)
            for part in metadata_parts
            if (
                part is not None
                and str(part).strip()
            )
        )

    @staticmethod
    def _normalize_reference_part(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = re.sub(
            r"[\s()]+",
            "",
            str(value),
        ).lower()

        return normalized or None

    @classmethod
    def _explicit_section_reference_mismatch(
        cls,
        claim: str,
        evidence: list[LegalEvidence],
    ) -> bool:
        """
        Deterministically validate explicit Section /
        Subsection references against structured
        evidence metadata.

        Lexical similarity must never authorize a
        conflicting explicit legal reference.
        """

        references = list(
            SECTION_REFERENCE_PATTERN.finditer(
                claim
            )
        )

        if not references:
            return False

        structured_evidence = [
            item
            for item in evidence
            if item.section_number
        ]

        # If there is no structured section metadata,
        # this validator cannot make a deterministic
        # reference decision. Normal grounding checks
        # continue instead.
        if not structured_evidence:
            return False

        for reference in references:
            claimed_section = (
                cls._normalize_reference_part(
                    reference.group(
                        "section"
                    )
                )
            )

            claimed_subsection = (
                cls._normalize_reference_part(
                    reference.group(
                        "subsection"
                    )
                )
            )

            reference_matched = False

            for item in structured_evidence:
                evidence_section = (
                    cls._normalize_reference_part(
                        item.section_number
                    )
                )

                if (
                    evidence_section
                    != claimed_section
                ):
                    continue

                # When the claim explicitly names a
                # subsection, structured evidence must
                # confirm that subsection too.
                if (
                    claimed_subsection
                    is not None
                ):
                    evidence_subsection = (
                        cls._normalize_reference_part(
                            item.subsection_number
                        )
                    )

                    if (
                        evidence_subsection
                        != claimed_subsection
                    ):
                        continue

                reference_matched = True
                break

            if not reference_matched:
                return True

        return False

    @staticmethod
    def _has_negation(
        text: str,
    ) -> bool:
        return bool(
            NEGATION_PATTERN.search(
                text
            )
        )

    @staticmethod
    def _concept_tokens_match(
        left: str,
        right: str,
    ) -> bool:
        if left == right:
            return True

        # Avoid fuzzy matching short words.
        if min(
            len(left),
            len(right),
        ) < 6:
            return False

        # Closely related legal/concept terms should
        # not differ dramatically in length.
        if abs(
            len(left) - len(right)
        ) > 4:
            return False

        # Handles forms such as:
        # secular -> secularism
        if (
            left.startswith(right)
            or right.startswith(left)
        ):
            return True

        # Require a meaningful common prefix before
        # considering fuzzy morphological similarity.
        shared_prefix_length = 0

        for left_char, right_char in zip(
            left,
            right,
        ):
            if left_char != right_char:
                break

            shared_prefix_length += 1

        if shared_prefix_length < 5:
            return False

        similarity = SequenceMatcher(
            None,
            left,
            right,
        ).ratio()

        return similarity >= 0.80

    @classmethod
    def _extract_explicit_absence_subjects(
        cls,
        claim: str,
    ) -> list[set[str]]:
        subjects: list[set[str]] = []

        for pattern in (
            EXPLICIT_ABSENCE_PATTERNS
        ):
            for match in pattern.finditer(
                claim
            ):
                subject = match.group(
                    "subject"
                ).strip()

                tokens = (
                    cls._tokenize(
                        subject
                    )
                    - ABSENCE_GENERIC_WORDS
                )

                if tokens:
                    subjects.append(
                        tokens
                    )

        return subjects

    @classmethod
    def _explicit_absence_is_contradicted(
        cls,
        claim: str,
        evidence: list[LegalEvidence],
    ) -> bool:
        subjects = (
            cls._extract_explicit_absence_subjects(
                claim
            )
        )

        if not subjects:
            return False

        for subject_tokens in subjects:
            for item in evidence:
                evidence_tokens = (
                    cls._tokenize(
                        item.content
                    )
                )

                all_terms_found = all(
                    any(
                        cls._concept_tokens_match(
                            subject_token,
                            evidence_token,
                        )
                        for evidence_token
                        in evidence_tokens
                    )
                    for subject_token
                    in subject_tokens
                )

                if all_terms_found:
                    return True

        return False

    @classmethod
    def _negation_mismatch_is_contradicted(
        cls,
        claim: str,
        evidence: list[LegalEvidence],
    ) -> bool:
        if not cls._has_negation(
            claim
        ):
            return False

        claim_tokens = (
            cls._tokenize(
                claim
            )
        )

        claim_tokens -= NEGATION_WORDS

        # Auxiliary verbs should not determine
        # proposition similarity.
        claim_tokens -= {
            "do",
            "does",
            "did",
            "is",
            "are",
            "was",
            "were",
        }

        if not claim_tokens:
            return False

        for item in evidence:
            segments = re.split(
                r"[\n.!?;]+",
                item.content,
            )

            for segment in segments:
                segment = (
                    segment.strip()
                )

                if not segment:
                    continue

                # A negative evidence sentence should
                # not trigger this simple polarity rule.
                if cls._has_negation(
                    segment
                ):
                    continue

                evidence_tokens = (
                    cls._tokenize(
                        segment
                    )
                )

                if not evidence_tokens:
                    continue

                overlap = (
                    len(
                        claim_tokens
                        & evidence_tokens
                    )
                    / len(
                        claim_tokens
                    )
                )

                # Intentionally high threshold.
                # This is only for obvious polarity
                # contradictions, not semantic NLI.
                if overlap >= 0.75:
                    return True

        return False

    @classmethod
    def _find_contradiction(
        cls,
        claim: str,
        evidence: list[LegalEvidence],
    ) -> str | None:
        if (
            cls._explicit_absence_is_contradicted(
                claim,
                evidence,
            )
        ):
            return (
                "Claim states that a concept is absent "
                "or not mentioned, but the cited legal "
                "evidence contains that concept."
            )

        if (
            cls._negation_mismatch_is_contradicted(
                claim,
                evidence,
            )
        ):
            return (
                "Claim negates a proposition that is "
                "strongly matched by affirmative cited "
                "legal evidence."
            )

        return None

    @classmethod
    def _validate_claim(
        cls,
        claim: str,
        citation_ids: list[str],
        evidence_map: dict[
            str,
            LegalEvidence,
        ],
        user_query: str | None = None,
    ) -> ClaimValidation:
        if not citation_ids:
            return ClaimValidation(
                claim=claim,
                citation_ids=[],
                support_level=(
                    ClaimSupportLevel.UNSUPPORTED
                ),
                reason=(
                    "Claim has no citation."
                ),
            )

        cited_evidence = [
            evidence_map[
                citation_id
            ]
            for citation_id
            in citation_ids
            if citation_id
            in evidence_map
        ]

        if not cited_evidence:
            return ClaimValidation(
                claim=claim,
                citation_ids=(
                    citation_ids
                ),
                support_level=(
                    ClaimSupportLevel.UNSUPPORTED
                ),
                reason=(
                    "Claim cites evidence "
                    "that was not supplied."
                ),
            )

        if re.search(r"\(\s*E\d+\s*\)", claim, flags=re.IGNORECASE):
            return ClaimValidation(
                claim=claim,
                citation_ids=citation_ids,
                support_level=ClaimSupportLevel.UNSUPPORTED,
                reason=(
                    "Claim contains an inline evidence citation marker. "
                    "Evidence IDs belong only in the citations array; "
                    "they are not legal subsection references."
                ),
            )

        if (
            cls._explicit_section_reference_mismatch(
                claim=claim,
                evidence=cited_evidence,
            )
        ):
            return ClaimValidation(
                claim=claim,
                citation_ids=citation_ids,
                support_level=(
                    ClaimSupportLevel.UNSUPPORTED
                ),
                reason=(
                    "Claim contains an explicit legal "
                    "section or subsection reference that "
                    "does not match the structured metadata "
                    "of the cited evidence."
                ),
            )

        penalty_reason = penalty_contradiction(claim, cited_evidence)
        if penalty_reason:
            return ClaimValidation(
             claim=claim,
             citation_ids=citation_ids,
             support_level=ClaimSupportLevel.UNSUPPORTED,
             reason=penalty_reason,
         )

        qualifier_mismatch = provocation_condition_mismatch(
            statement=claim,
            evidence=cited_evidence,
            user_query=user_query,
        )

        if qualifier_mismatch is not None:
            return ClaimValidation(
                claim=claim,
                citation_ids=citation_ids,
                support_level=ClaimSupportLevel.UNSUPPORTED,
                reason=PROVOCATION_CONDITION_MISMATCH_REASON,
            )

        contradiction_reason = (
            cls._find_contradiction(
                claim,
                cited_evidence,
            )
        )

        if contradiction_reason:
            return ClaimValidation(
                claim=claim,
                citation_ids=(
                    citation_ids
                ),
                support_level=(
                    ClaimSupportLevel.UNSUPPORTED
                ),
                reason=(
                    contradiction_reason
                ),
            )

        claim_tokens = (
            cls._tokenize(
                claim
            )
        )

        if not claim_tokens:
            return ClaimValidation(
                claim=claim,
                citation_ids=(
                    citation_ids
                ),
                support_level=(
                    ClaimSupportLevel.UNSUPPORTED
                ),
                reason=(
                    "Claim does not contain enough "
                    "meaningful terms for baseline "
                    "grounding."
                ),
            )

        best_overlap = 0.0

        for evidence in cited_evidence:
            grounding_text = (
                cls._evidence_grounding_text(
                    evidence
                )
            )

            evidence_tokens = (
                cls._tokenize(
                    grounding_text
                )
            )

            if not evidence_tokens:
                continue

            matched_claim_tokens = {
                claim_token
                for claim_token
                in claim_tokens
                if any(
                    cls._concept_tokens_match(
                        claim_token,
                        evidence_token,
                    )
                    for evidence_token
                    in evidence_tokens
                )
            }

            overlap = (
                len(
                    matched_claim_tokens
                )
                / len(
                    claim_tokens
                )
            )

            best_overlap = max(
                best_overlap,
                overlap,
            )

        if best_overlap >= 0.60:
            support_level = (
                ClaimSupportLevel.SUPPORTED
            )

            reason = (
                "Claim has strong lexical "
                "overlap with the cited "
                "legal evidence."
            )

        elif best_overlap >= 0.30:
            support_level = (
                ClaimSupportLevel.PARTIALLY_SUPPORTED
            )

            reason = (
                "Claim has partial lexical "
                "overlap with the cited "
                "legal evidence."
            )

        else:
            support_level = (
                ClaimSupportLevel.UNSUPPORTED
            )

            reason = (
                "Claim has insufficient lexical "
                "overlap with the cited "
                "legal evidence."
            )

        return ClaimValidation(
            claim=claim,
            citation_ids=citation_ids,
            support_level=support_level,
            reason=reason,
        )

    @classmethod
    def validate(
        cls,
        answer: LegalAnswer,
        evidence: list[
            LegalEvidence
        ],
        user_query: str | None = None,
    ) -> ClaimValidationResult:
        evidence_map = {
            item.citation_id: item
            for item in evidence
            if item.citation_id
        }

        claims: list[
            ClaimValidation
        ] = []

        answer_claims = [
            answer.summary,
            *answer.legal_basis,
            *answer.possible_options,
            *answer.next_steps,
        ]

        for claim in answer_claims:
            validation = (
                cls._validate_claim(
                    claim=claim,
                    citation_ids=(
                        answer.citations
                    ),
                    evidence_map=(
                        evidence_map
                    ),
                    user_query=user_query,
                )
            )

            claims.append(
                validation
            )

        supported_claims = [
            item.claim
            for item in claims
            if (
                item.support_level
                == ClaimSupportLevel.SUPPORTED
            )
        ]

        partially_supported_claims = [
            item.claim
            for item in claims
            if (
                item.support_level
                == ClaimSupportLevel.PARTIALLY_SUPPORTED
            )
        ]

        unsupported_claims = [
            item.claim
            for item in claims
            if (
                item.support_level
                == ClaimSupportLevel.UNSUPPORTED
            )
        ]

        validation_reasons = [
            item.reason
            for item in claims
        ]

        return ClaimValidationResult(
            is_valid=(
                len(
                    unsupported_claims
                )
                == 0
            ),
            claims=claims,
            supported_claims=(
                supported_claims
            ),
            partially_supported_claims=(
                partially_supported_claims
            ),
            unsupported_claims=(
                unsupported_claims
            ),
            validation_reasons=(
                validation_reasons
            ),
        )
