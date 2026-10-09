import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.schemas.answer_integrity import (
    AnswerIntegrityIssue,
    AnswerIntegrityResult,
)
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.services.legal_qualifier_grounding import (
    provocation_condition_mismatch,
)


TOKEN_PATTERN = re.compile(
    r"[a-zA-Z0-9]+"
)


QUALIFIER_PATTERN = re.compile(
    r"\b("
    r"provided\s+that|"
    r"provided\s+further\s+that|"
    r"if|"
    r"where|"
    r"unless|"
    r"except|"
    r"subject\s+to|"
    r"in\s+case\s+of|"
    r"in\s+cases\s+of|"
    r"when"
    r")\b",
    flags=re.IGNORECASE,
)


CONSEQUENCE_PATTERN = re.compile(
    r"\b("
    r"shall\s+be\s+punished|"
    r"may\s+be\s+punished|"
    r"is\s+punishable|"
    r"shall\s+be\s+liable|"
    r"is\s+liable|"
    r"shall\s+apply|"
    r"may\s+apply|"
    r"applies|"
    r"shall\s+be\s+entitled|"
    r"may\s+be\s+entitled|"
    r"punishment\s+is"
    r")\b",
    flags=re.IGNORECASE,
)


SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?])\s+|\n+"
)


CONDITION_SPLIT_PATTERN = re.compile(
    r"\s*(?:,|;|\band\b)\s*",
    flags=re.IGNORECASE,
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
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


QUALIFIER_BOILERPLATE = {
    "provided",
    "further",
    "where",
    "if",
    "when",
    "unless",
    "except",
    "subject",
    "case",
    "cases",
    "shall",
    "may",
    "be",
}


PENALTY_QUERY_HINTS = {
    "punishment",
    "punish",
    "punished",
    "penalty",
    "sentence",
    "sentenced",
    "imprisonment",
    "fine",
    "years",
    "year",
}


PENALTY_STATEMENT_HINTS = {
    "punishment",
    "punish",
    "punished",
    "punishable",
    "penalty",
    "imprisonment",
    "fine",
    "liable",
    "sentence",
    "sentenced",
    "years",
    "year",
    "community",
    "service",
}


DISTINCTIVE_IGNORE_TOKENS = {
    "person",
    "persons",
    "offence",
    "offender",
    "law",
    "legal",
    "section",
    "subsection",
    "act",
    "provision",
    "punishment",
    "punished",
    "punishable",
    "shall",
    "may",
    "imprisonment",
    "fine",
    "term",
}

DIGIT_NUMBER_PATTERN = re.compile(
    r"(?<!\w)\d[\d,]*(?:\.\d+)?"
)


NUMBER_WORD_VALUES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


NUMBER_SCALE_VALUES = {
    "thousand": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
}


ORDINAL_VALUES = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}


@dataclass
class _QualifiedRule:
    citation_id: str | None
    section_number: str | None

    condition_groups: list[
        set[str]
    ]

    condition_numeric_values: set[str]

    consequence_tokens: set[str]


class LegalAnswerIntegrityValidator:
    @staticmethod
    def _tokenize(
        text: str,
    ) -> set[str]:
        tokens = {
            token.lower()
            for token
            in TOKEN_PATTERN.findall(
                text
            )
        }

        return {
            token
            for token in tokens
            if (
                len(token) >= 2
                and token not in STOPWORDS
            )
        }

    @classmethod
    def _material_tokens(
        cls,
        text: str,
    ) -> set[str]:
        return (
            cls._tokenize(text)
            - QUALIFIER_BOILERPLATE
        )

    @classmethod
    def _numeric_values(
        cls,
        text: str,
    ) -> set[str]:
        values: set[str] = set()

        # -------------------------------------------------
        # Numeric forms such as:
        #
        # 5000
        # 5,000
        # 3.5
        # -------------------------------------------------

        for match in (
            DIGIT_NUMBER_PATTERN.finditer(
                text
            )
        ):
            raw_value = (
                match.group(0)
                .replace(",", "")
            )

            if "." in raw_value:
                raw_value = (
                    raw_value
                    .rstrip("0")
                    .rstrip(".")
                )

            if raw_value.isdigit():
                raw_value = str(
                    int(raw_value)
                )

            values.add(
                raw_value
            )

        # -------------------------------------------------
        # Word forms such as:
        #
        # five thousand  -> 5000
        # three          -> 3
        # one lakh       -> 100000
        # first          -> 1
        # -------------------------------------------------

        tokens = [
            token.lower()
            for token
            in TOKEN_PATTERN.findall(
                text
            )
        ]

        total = 0
        current = 0
        active = False

        def flush_number() -> None:
            nonlocal total
            nonlocal current
            nonlocal active

            if active:
                values.add(
                    str(
                        total + current
                    )
                )

            total = 0
            current = 0
            active = False

        for token in tokens:
            if token in ORDINAL_VALUES:
                flush_number()

                values.add(
                    str(
                        ORDINAL_VALUES[
                            token
                        ]
                    )
                )

                continue

            if token in NUMBER_WORD_VALUES:
                active = True

                current += (
                    NUMBER_WORD_VALUES[
                        token
                    ]
                )

                continue

            if (
                token == "hundred"
                and active
            ):
                current = max(
                    current,
                    1,
                ) * 100

                continue

            if token in NUMBER_SCALE_VALUES:
                active = True

                scale = (
                    NUMBER_SCALE_VALUES[
                        token
                    ]
                )

                total += max(
                    current,
                    1,
                ) * scale

                current = 0

                continue

            if (
                token == "and"
                and active
            ):
                continue

            flush_number()

        flush_number()

        return values

    @staticmethod
    def _tokens_match(
        left: str,
        right: str,
    ) -> bool:
        if left == right:
            return True

        if min(
            len(left),
            len(right),
        ) < 5:
            return False

        if abs(
            len(left)
            - len(right)
        ) > 4:
            return False

        if (
            left.startswith(right)
            or right.startswith(left)
        ):
            return True

        similarity = SequenceMatcher(
            None,
            left,
            right,
        ).ratio()

        return similarity >= 0.82

    @classmethod
    def _matched_count(
        cls,
        source_tokens: set[str],
        target_tokens: set[str],
    ) -> int:
        return sum(
            1
            for source_token
            in source_tokens
            if any(
                cls._tokens_match(
                    source_token,
                    target_token,
                )
                for target_token
                in target_tokens
            )
        )

    @classmethod
    def _coverage(
        cls,
        source_tokens: set[str],
        target_tokens: set[str],
    ) -> float:
        if not source_tokens:
            return 0.0

        return (
            cls._matched_count(
                source_tokens,
                target_tokens,
            )
            / len(source_tokens)
        )

    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:
        return [
            part.strip()
            for part
            in SENTENCE_SPLIT_PATTERN.split(
                text
            )
            if part.strip()
        ]

    @classmethod
    def _extract_qualified_rules(
        cls,
        evidence: LegalEvidence,
    ) -> list[_QualifiedRule]:
        rules: list[
            _QualifiedRule
        ] = []

        units = cls._split_sentences(
            evidence.content
        )

        for unit in units:
            qualifier_match = (
                QUALIFIER_PATTERN.search(
                    unit
                )
            )

            if qualifier_match is None:
                continue

            remaining = unit[
                qualifier_match.end():
            ]

            consequence_matches = list(
                CONSEQUENCE_PATTERN.finditer(
                    remaining
                )
            )

            if not consequence_matches:
                continue

            # Use the final consequence marker.
            #
            # This matters for rules such as:
            #
            #   provided that ...
            #   upon condition X ...
            #   shall be punished ...
            #
            # Everything before the final legal
            # consequence remains part of the
            # qualifying conditions.
            consequence_match = (
                consequence_matches[-1]
            )

            condition_text = remaining[
                :consequence_match.start()
            ]

            condition_numeric_values = (
                cls._numeric_values(
                    condition_text
                )
            )

            consequence_text = remaining[
                consequence_match.start():
            ]

            raw_groups = (
                CONDITION_SPLIT_PATTERN.split(
                    condition_text
                )
            )

            condition_groups: list[
                set[str]
            ] = []

            for raw_group in raw_groups:
                tokens = (
                    cls._material_tokens(
                        raw_group
                    )
                )

                if len(tokens) >= 2:
                    condition_groups.append(
                        tokens
                    )

            consequence_tokens = (
                cls._material_tokens(
                    consequence_text
                )
            )

            if (
                not condition_groups
                or not consequence_tokens
            ):
                continue

            rules.append(
                _QualifiedRule(
                    citation_id=(
                        evidence.citation_id
                    ),
                    section_number=(
                        evidence.section_number
                    ),
                    condition_groups=(
                        condition_groups
                    ),
                    condition_numeric_values=(
                        condition_numeric_values
                    ),
                    consequence_tokens=(
                        consequence_tokens
                    ),
                )
            )

        return rules


    @classmethod
    def _statement_matches_rule(
        cls,
        statement: str,
        rule: _QualifiedRule,
    ) -> bool:
        statement_tokens = (
            cls._material_tokens(
                statement
            )
        )

        if not statement_tokens:
            return False

        consequence_coverage = (
            cls._coverage(
                rule.consequence_tokens,
                statement_tokens,
            )
        )

        if consequence_coverage < 0.50:
            return False

        # Generic legal wording alone cannot identify a qualified rule.
        condition_tokens = (
            set().union(*rule.condition_groups)
            - DISTINCTIVE_IGNORE_TOKENS
            - {"any", "under"}
        )
        if condition_tokens and not cls._matched_count(
            condition_tokens,
            statement_tokens,
        ):
            return False

        group_coverages = [
            cls._coverage(
                group,
                statement_tokens,
            )
            for group
            in rule.condition_groups
        ]

        # Avoid treating a generic mention of the
        # consequence as a paraphrase of the
        # qualified rule.
        return any(
            coverage >= 0.35
            for coverage
            in group_coverages
        )

    @classmethod
    def _qualified_rule_is_complete(
        cls,
        statement: str,
        rule: _QualifiedRule,
    ) -> bool:
        statement_tokens = (
            cls._material_tokens(
                statement
            )
        )

        for index, condition_group in enumerate(
            rule.condition_groups
        ):
            if cls._coverage(
                condition_group,
                statement_tokens,
            ) < 0.35:
                return False

            sibling_tokens = set().union(
                *(
                    sibling_group
                    for sibling_index, sibling_group
                    in enumerate(
                        rule.condition_groups
                    )
                    if sibling_index != index
                )
            )

            distinctive_tokens = (
                condition_group
                - sibling_tokens
                - DISTINCTIVE_IGNORE_TOKENS
                - {"any", "under"}
            )

            # Shared nouns can make an omitted conjunct
            # appear complete by token coverage alone.
            # When a condition group has wording that is
            # distinct from its sibling groups, require at
            # least one such anchor in the generated rule.
            if (
                distinctive_tokens
                and not cls._matched_count(
                    distinctive_tokens,
                    statement_tokens,
                )
            ):
                return False

        return True

    @classmethod
    def _qualified_rule_has_numeric_mismatch(
        cls,
        statement: str,
        rule: _QualifiedRule,
    ) -> bool:
        required_values = (
            rule.condition_numeric_values
        )

        if not required_values:
            return False

        statement_values = (
            cls._numeric_values(
                statement
            )
        )

        return not (
            required_values
            <= statement_values
        )

    @classmethod
    def _query_supports_rule(
        cls,
        user_query: str,
        rule: _QualifiedRule,
    ) -> bool:
        # Explicit requests for a particular section
        # are allowed even if the user does not restate
        # every factual trigger.

        if rule.section_number:
            section_number = re.escape(
                str(
                    rule.section_number
                )
            )

            reference_pattern = re.compile(
                rf"\bsection\s+"
                rf"{section_number}\b",
                flags=re.IGNORECASE,
            )

            if reference_pattern.search(
                user_query
            ):
                return True

        query_tokens = (
            cls._material_tokens(
                user_query
            )
        )

        if not query_tokens:
            return False

        # Every material condition group must have
        # meaningful support in the user's query.
        #
        # One incidental matching word is not enough.

        return all(
            cls._coverage(
                condition_group,
                query_tokens,
            )
            >= 0.35
            for condition_group
            in rule.condition_groups
        )

    @classmethod
    def _qualifier_issues(
        cls,
        answer: LegalAnswer,
        evidence: list[
            LegalEvidence
        ],
    ) -> list[
        AnswerIntegrityIssue
    ]:
        issues: list[
            AnswerIntegrityIssue
        ] = []

        summary_sentences = (
            cls._split_sentences(
                answer.summary
            )
        )

        statements: list[
            tuple[str, str]
        ] = [
            (
                "summary",
                sentence,
            )
            for sentence
            in summary_sentences
        ]

        for field_name, values in (
            (
                "legal_basis",
                answer.legal_basis,
            ),
            (
                "possible_options",
                answer.possible_options,
            ),
            (
                "next_steps",
                answer.next_steps,
            ),
        ):
            for value in values:
                for sentence in (
                    cls._split_sentences(
                        value
                    )
                ):
                    statements.append(
                        (
                            field_name,
                            sentence,
                        )
                    )

        qualified_rules: list[
            _QualifiedRule
        ] = []

        for item in evidence:
            qualified_rules.extend(
                cls._extract_qualified_rules(
                    item
                )
            )

        for rule in qualified_rules:
            matching_summary_sentences: list[
                str
            ] = []

            for (
                field_name,
                sentence,
            ) in statements:
                if not (
                    cls._statement_matches_rule(
                        sentence,
                        rule,
                    )
                ):
                    continue

                if field_name == "summary":
                    matching_summary_sentences.append(
                        sentence
                    )

                if (
                    cls._qualified_rule_has_numeric_mismatch(
                        sentence,
                        rule,
                    )
                ):
                    issues.append(
                        AnswerIntegrityIssue(
                            code=(
                                "mismatched_numeric_value"
                            ),
                            message=(
                                "A generated legal rule "
                                "changed or omitted a "
                                "material numeric condition "
                                "found in the verified "
                                "evidence."
                            ),
                            claim=sentence,
                            citation_id=(
                                rule.citation_id
                            ),
                        )
                    )

                    continue

                if not (
                    cls._qualified_rule_is_complete(
                        sentence,
                        rule,
                    )
                ):
                    issues.append(
                        AnswerIntegrityIssue(
                            code=(
                                "incomplete_qualified_rule"
                            ),
                            message=(
                                "A conditional legal "
                                "consequence was stated "
                                "without all material "
                                "conditions found in the "
                                "verified evidence."
                            ),
                            claim=sentence,
                            citation_id=(
                                rule.citation_id
                            ),
                        )
                    )

            # Repetition is deliberately checked only
            # inside the summary. A legal rule appearing
            # once in summary and once in legal_basis is
            # structurally normal.

            if len(
                matching_summary_sentences
            ) > 1:
                issues.append(
                    AnswerIntegrityIssue(
                        code=(
                            "duplicate_qualified_rule"
                        ),
                        message=(
                            "The same qualified legal "
                            "rule appears multiple times "
                            "in the summary."
                        ),
                        claim=(
                            " | ".join(
                                matching_summary_sentences
                            )
                        ),
                        citation_id=(
                            rule.citation_id
                        ),
                    )
                )

        return issues

    @classmethod
    def _best_matching_evidence(
        cls,
        statement: str,
        evidence: list[
            LegalEvidence
        ],
    ) -> LegalEvidence | None:
        statement_tokens = (
            cls._material_tokens(
                statement
            )
        )

        if not statement_tokens:
            return None

        best_item: (
            LegalEvidence | None
        ) = None

        best_score = 0.0

        for item in evidence:
            evidence_tokens = (
                cls._material_tokens(
                    item.content
                )
            )

            if not evidence_tokens:
                continue

            score = cls._coverage(
                statement_tokens,
                evidence_tokens,
            )

            if score > best_score:
                best_score = score
                best_item = item

        return best_item

    @classmethod
    def _is_penalty_query(
        cls,
        query: str,
    ) -> bool:
        query_tokens = (
            cls._tokenize(
                query
            )
        )

        return bool(
            query_tokens
            & PENALTY_QUERY_HINTS
        )

    @classmethod
    def _is_penalty_statement(
        cls,
        statement: str,
    ) -> bool:
        tokens = cls._tokenize(
            statement
        )

        return bool(
            tokens
            & PENALTY_STATEMENT_HINTS
        )

    @classmethod
    def _omitted_qualified_rule_issues(
        cls,
        user_query: str,
        answer: LegalAnswer,
        evidence: list[
            LegalEvidence
        ],
    ) -> list[
        AnswerIntegrityIssue
    ]:
        # -------------------------------------------------
        # This check is intentionally conservative.
        #
        # It applies only to penalty questions and only
        # to evidence that the generated answer itself
        # cites.
        #
        # It does NOT require every qualified rule from
        # every retrieved chunk to be reproduced.
        # -------------------------------------------------

        if not cls._is_penalty_query(
            user_query
        ):
            return []

        if not evidence:
            return []

        cited_ids = {
            citation_id
            for citation_id
            in answer.citations
        }

        if not cited_ids:
            return []

        cited_evidence = [
            item
            for item in evidence
            if (
                item.citation_id
                and item.citation_id
                in cited_ids
            )
        ]

        if not cited_evidence:
            return []

        # -------------------------------------------------
        # Determine which of the actually cited evidence
        # items most directly matches the user's question.
        #
        # This avoids treating every retrieved special
        # provision as something that must be mentioned.
        # -------------------------------------------------

        controlling_evidence = (
            cls._best_matching_evidence(
                user_query,
                cited_evidence,
            )
        )

        if controlling_evidence is None:
            return []

        qualified_rules = (
            cls._extract_qualified_rules(
                controlling_evidence
            )
        )

        if not qualified_rules:
            return []

        # -------------------------------------------------
        # This omission check is for broad penalty
        # questions.
        #
        # If the query itself supplies the factual
        # conditions of a qualified rule, it is a
        # condition-specific question rather than the
        # broad-overview case handled here.
        # -------------------------------------------------

        if any(
            cls._query_supports_rule(
                user_query,
                rule,
            )
            for rule
            in qualified_rules
        ):
            return []

        statements: list[str] = []

        statements.extend(
            cls._split_sentences(
                answer.summary
            )
        )

        for legal_basis_item in (
            answer.legal_basis
        ):
            statements.extend(
                cls._split_sentences(
                    legal_basis_item
                )
            )

        issues: list[
            AnswerIntegrityIssue
        ] = []

        for rule in qualified_rules:
            # Only consequences that are themselves
            # punishment / penalty rules are required
            # by this check.

            if not (
                rule.consequence_tokens
                & PENALTY_STATEMENT_HINTS
            ):
                continue

            rule_is_represented = any(
                cls._statement_matches_rule(
                    statement,
                    rule,
                )
                for statement
                in statements
            )

            if rule_is_represented:
                continue

                        # Diagnostic only: a partial mention never passes validation.
            condition_tokens = (
                set().union(*rule.condition_groups)
                - DISTINCTIVE_IGNORE_TOKENS
                - {"any", "under"}
            )
            partial_statement = None

            for statement in statements:
                statement_tokens = cls._material_tokens(statement)
                if (
                    cls._coverage(
                        rule.consequence_tokens,
                        statement_tokens,
                    ) >= 0.50
                    and cls._matched_count(
                        condition_tokens,
                        statement_tokens,
                    ) >= 2
                ):
                    partial_statement = statement
                    break

            if partial_statement is not None:
                issues.append(
                    AnswerIntegrityIssue(
                        code="incomplete_qualified_rule",
                        message=(
                            "A possible partial statement of a qualified "
                            "rule was found, but its completeness could "
                            "not be established against verified evidence."
                        ),
                        claim=partial_statement,
                        citation_id=rule.citation_id,
                    )
                )
                continue

            issues.append(
                AnswerIntegrityIssue(
                    code=(
                        "omitted_qualified_rule"
                    ),
                    message=(
                        "A broad penalty answer omitted "
                        "a material qualified punishment "
                        "contained in the controlling "
                        "cited legal evidence."
                    ),
                    claim=None,
                    citation_id=(
                        rule.citation_id
                    ),
                )
            )

        return issues

    @classmethod
    def _special_rule_issues(
        cls,
        user_query: str,
        answer: LegalAnswer,
        evidence: list[
            LegalEvidence
        ],
    ) -> list[
        AnswerIntegrityIssue
    ]:
        if len(evidence) < 2:
            return []

        if not cls._is_penalty_query(
            user_query
        ):
            return []

        primary = evidence[0]

        primary_tokens = (
            cls._material_tokens(
                primary.content
            )
        )

        query_tokens = (
            cls._material_tokens(
                user_query
            )
        )

        issues: list[
            AnswerIntegrityIssue
        ] = []

        for sentence in (
            cls._split_sentences(
                answer.summary
            )
        ):
            if not cls._is_penalty_statement(
                sentence
            ):
                continue

            best_evidence = (
                cls._best_matching_evidence(
                    sentence,
                    evidence,
                )
            )

            if best_evidence is None:
                continue

            if (
                best_evidence.chunk_id
                == primary.chunk_id
            ):
                continue

            # Multiple chunks from the same section
            # may simply represent chunking of one
            # controlling legal provision.
            if (
                primary.section_number
                and best_evidence.section_number
                and (
                    primary.section_number
                    == best_evidence.section_number
                )
            ):
                continue

            special_rules = (
                cls._extract_qualified_rules(
                    best_evidence
                )
            )

            matching_special_rules = [
                rule
                for rule
                in special_rules
                if cls._statement_matches_rule(
                    sentence,
                    rule,
                )
            ]

            if matching_special_rules:
                if any(
                    cls._query_supports_rule(
                        user_query,
                        rule,
                    )
                    for rule
                    in matching_special_rules
                ):
                    continue

                issues.append(
                    AnswerIntegrityIssue(
                        code=(
                            "unrequested_special_rule"
                        ),
                        message=(
                            "The answer introduced a "
                            "special or aggravated legal "
                            "rule whose material "
                            "triggering conditions were "
                            "not supplied in the user's "
                            "query."
                        ),
                        claim=sentence,
                        citation_id=(
                            best_evidence.citation_id
                        ),
                    )
                )

                continue

            best_tokens = (
                cls._material_tokens(
                    best_evidence.content
                )
            )

            distinctive_tokens = (
                best_tokens
                - primary_tokens
                - DISTINCTIVE_IGNORE_TOKENS
            )

            if not distinctive_tokens:
                continue

            sentence_tokens = (
                cls._material_tokens(
                    sentence
                )
            )

            statement_matches = (
                cls._matched_count(
                    distinctive_tokens,
                    sentence_tokens,
                )
            )

            query_matches = (
                cls._matched_count(
                    distinctive_tokens,
                    query_tokens,
                )
            )

            # Conservative gate:
            #
            # The generated sentence must strongly
            # depend on facts unique to a lower-ranked
            # provision, while the user's query contains
            # none of those distinctive facts.
            if (
                statement_matches >= 3
                and query_matches == 0
            ):
                issues.append(
                    AnswerIntegrityIssue(
                        code=(
                            "unrequested_special_rule"
                        ),
                        message=(
                            "The answer introduced a "
                            "special or aggravated legal "
                            "rule whose distinctive "
                            "triggering circumstances "
                            "were not supplied in the "
                            "user's query."
                        ),
                        claim=sentence,
                        citation_id=(
                            best_evidence.citation_id
                        ),
                    )
                )

        return issues

    @classmethod
    def _legal_qualifier_polarity_issues(
        cls,
        user_query: str,
        answer: LegalAnswer,
        evidence: list[LegalEvidence],
    ) -> list[AnswerIntegrityIssue]:
        issues: list[AnswerIntegrityIssue] = []
        seen: set[tuple[str, str | None]] = set()

        statements = [
            answer.summary,
            *answer.legal_basis,
            *answer.possible_options,
            *answer.next_steps,
        ]

        for statement in statements:
            mismatch = provocation_condition_mismatch(
                statement=statement,
                evidence=evidence,
                user_query=user_query,
            )

            if mismatch is None:
                continue

            key = (
                statement,
                mismatch.citation_id,
            )

            if key in seen:
                continue

            seen.add(key)
            issues.append(
                AnswerIntegrityIssue(
                    code="contradictory_legal_qualifier",
                    message=(
                        "The answer applied a provision using a "
                        "provocation condition that contradicts "
                        "the cited legal evidence."
                    ),
                    claim=statement,
                    citation_id=mismatch.citation_id,
                )
            )

        return issues

    @classmethod
    def validate(
        cls,
        user_query: str,
        answer: LegalAnswer,
        evidence: list[
            LegalEvidence
        ],
    ) -> AnswerIntegrityResult:
        issues: list[
            AnswerIntegrityIssue
        ] = []

        issues.extend(
            cls._legal_qualifier_polarity_issues(
                user_query=user_query,
                answer=answer,
                evidence=evidence,
            )
        )

        issues.extend(
            cls._qualifier_issues(
                answer=answer,
                evidence=evidence,
            )
        )

        issues.extend(
            cls._special_rule_issues(
                user_query=user_query,
                answer=answer,
                evidence=evidence,
            )
        )

        issues.extend(
            cls._omitted_qualified_rule_issues(
                user_query=user_query,
                answer=answer,
                evidence=evidence,
            )
        )

        return AnswerIntegrityResult(
            is_valid=(
                len(issues) == 0
            ),
            issues=issues,
        )
