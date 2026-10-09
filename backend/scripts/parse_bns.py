from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette_clean.txt"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_parsed.txt"
)


# Matches BNS section headings such as:
#
# 2.In this Sanhita...
# 303.(1) Whoever...
# 304. (1) Theft is snatching...
# 305.Whoever commits theft—
#
# (?!\d) prevents PDF metadata such as:
#
# 2.5.4.20=e8b886...
#
# from being interpreted as Section 2.
SECTION_PATTERN = re.compile(
    r"^(\d{1,3})\.(?!\d)\s*(.+)$"
)


# Matches:
#
# (1) text
# (2) text
SUBSECTION_PATTERN = re.compile(
    r"^\((\d+)\)\s*(.*)$"
)


# Matches:
#
# (a) text
# (b) text
# (i) text
CLAUSE_PATTERN = re.compile(
    r"^\(([a-z]+)\)\s*(.*)$"
)


# Detects an Illustrations. marker at the end
# of a line.
#
# Examples:
#
# Illustrations.
#
# commits theft. Illustrations.
ILLUSTRATIONS_PATTERN = re.compile(
    r"(?:^|\s)Illustrations\.\s*$",
    re.IGNORECASE,
)

PAGE_MARKER_PATTERN = re.compile(
    r"^===== PAGE \d+ =====$"
)

END_OF_ACT_PATTERN = re.compile(
    r"^[—–-](?:\s*[—–-]){2,}\s*$"
)

CHAPTER_PATTERN = re.compile(
    r"^CHAPTER\s+[IVXLCDM]+$",
    re.IGNORECASE,
)

OF_HEADING_PATTERN = re.compile(
    r"^Of\s+.+$"
)

UPPERCASE_HEADING_PATTERN = re.compile(
    r"^[A-Z][A-Z\s&,-]{3,}$"
)

SINGULAR_ILLUSTRATION_PATTERN = re.compile(
    r"^Illustration\.\s*$",
    re.IGNORECASE,
)

ROMAN_NUMERAL_PATTERN = re.compile(
    r"^[ivxlcdm]+$"
)

SUPPLEMENTARY_EXPLANATION_PATTERN = re.compile(
    r"^Explanation(?:s)?\.\s*[—–-]?",
    re.IGNORECASE,
)

SUPPLEMENTARY_EXCEPTION_PATTERN = re.compile(
    r"^Exception(?:s)?\.\s*[—–-]?",
    re.IGNORECASE,
)

SUPPLEMENTARY_PROVISO_PATTERN = re.compile(
    r"^Provided\s+that\b",
    re.IGNORECASE,
)

def supplementary_scope(
    line: str,
) -> str | None:
    """
    Return the ownership scope for a supplementary
    statutory block.

    - Explanation -> current subsection when present.
    - Provided that -> current subsection.
    - Exception saying "this section" -> Section.
    - Other Exception -> current subsection by default.
    """

    if SUPPLEMENTARY_EXPLANATION_PATTERN.match(
        line
    ):
        return "subsection"

    if SUPPLEMENTARY_PROVISO_PATTERN.match(
        line
    ):
        return "subsection"

    if SUPPLEMENTARY_EXCEPTION_PATTERN.match(
        line
    ):
        if re.search(
            r"\bthis\s+section\b",
            line,
            re.IGNORECASE,
        ):
            return "section"

        return "subsection"

    return None

def subsection_number_value(
    number: str,
) -> int:
    return int(
        number.strip("()")
    )


def should_start_new_subsection(
    candidate_number: str,
    current_subsection,
) -> bool:
    """
    A genuine BNS subsection proceeds sequentially.

    This prevents wrapped statutory text such as:

        (3), (4) and (5) of section 8 ...

    from being mistaken for another subsection when
    the parser is already much later in the section.
    """

    if current_subsection is None:
        return True

    current_number = (
        subsection_number_value(
            current_subsection["number"]
        )
    )

    candidate_value = int(
        candidate_number
    )

    return (
        candidate_value
        == current_number + 1
    )


def roman_to_int(
    value: str,
) -> int:
    values = {
        "i": 1,
        "v": 5,
        "x": 10,
        "l": 50,
        "c": 100,
        "d": 500,
        "m": 1000,
    }

    total = 0
    previous = 0

    for character in reversed(
        value.lower()
    ):
        current = values[
            character
        ]

        if current < previous:
            total -= current
        else:
            total += current
            previous = current

    return total


def infer_clause_style(
    label: str,
) -> str:
    """
    Determine the style of the top-level list.

    First '(a)' means alphabetic clauses.
    First '(i)'/'(ii)' means Roman clauses.

    Once chosen, the style does not change merely
    because an alphabetic list later reaches '(i)'.
    """

    label = label.lower()

    if (
        label == "i"
        or (
            len(label) > 1
            and ROMAN_NUMERAL_PATTERN.fullmatch(
                label
            )
        )
    ):
        return "roman"

    return "alpha"


def should_start_new_clause(
    candidate_label: str,
    clause_style: str | None,
    last_top_level_label: str | None,
) -> tuple[bool, str]:
    """
    Decide whether a marker is a new top-level Clause
    or a nested/restarted item.

    Examples:

        (a)
            (i)   <- nested
            (ii)  <- nested
        (b)       <- next top-level clause

    and:

        (i)
        (ii)
        Provided that—
            (i)   <- restarted nested item
            (ii)  <- restarted nested item
    """

    candidate = (
        candidate_label.lower()
    )

    if last_top_level_label is None:
        style = infer_clause_style(
            candidate
        )

        return True, style

    if clause_style == "alpha":

        previous = (
            last_top_level_label.lower()
        )

        if (
            len(previous) == 1
            and len(candidate) == 1
            and candidate.isalpha()
            and ord(candidate)
            == ord(previous) + 1
        ):
            return True, clause_style

        return False, clause_style

    if clause_style == "roman":

        if not (
            ROMAN_NUMERAL_PATTERN.fullmatch(
                candidate
            )
        ):
            return False, clause_style

        if (
            roman_to_int(candidate)
            == roman_to_int(
                last_top_level_label
            )
            + 1
        ):
            return True, clause_style

        return False, clause_style

    raise RuntimeError(
        "Unknown clause numbering style."
    )


def is_expected_next_top_level_clause(
    candidate_label: str,
    clause_style: str | None,
    last_top_level_label: str | None,
) -> bool:
    if (
        clause_style is None
        or last_top_level_label is None
    ):
        return False

    candidate = candidate_label.lower()
    previous = last_top_level_label.lower()

    if clause_style == "alpha":
        return (
            len(previous) == 1
            and len(candidate) == 1
            and previous.isalpha()
            and candidate.isalpha()
            and ord(candidate)
            == ord(previous) + 1
        )

    if clause_style == "roman":
        if not (
            ROMAN_NUMERAL_PATTERN.fullmatch(
                candidate
            )
        ):
            return False

        return (
            roman_to_int(candidate)
            == roman_to_int(previous) + 1
        )

    return False


def should_exit_nested_clause_list(
    candidate_label: str,
    clause_style: str | None,
    last_top_level_label: str | None,
    can_return_to_top_level: bool,
) -> bool:
    """
    A nested list may return to the parent top-level
    sequence only when:

    1. the nested sequence began in a DIFFERENT
       numbering style; and
    2. the candidate is exactly the expected next
       parent-level marker.

    Example:

        top-level (a)
            nested (i)
            nested (ii)
        top-level (b)

    But when a Roman list restarts inside another
    Roman list:

        top-level (i)
        top-level (ii)
        Provided that—
            nested (i)
            nested (ii)
            nested (iii)

    we stay nested until the subsection ends.
    """

    if not can_return_to_top_level:
        return False

    return is_expected_next_top_level_clause(
        candidate_label,
        clause_style,
        last_top_level_label,
    )


def split_illustrations_marker(
    line: str,
) -> tuple[str, bool]:
    plural_match = (
        ILLUSTRATIONS_PATTERN.search(
            line
        )
    )

    if plural_match is not None:
        return (
            line[
                :plural_match.start()
            ].rstrip(),
            True,
        )

    if (
        SINGULAR_ILLUSTRATION_PATTERN
        .match(line)
    ):
        return "", True

    return line, False


def parse_section_header(
    line: str,
):
    section_match = SECTION_PATTERN.match(
        line
    )

    if section_match is None:
        return None

    section_number = (
        section_match.group(1)
    )

    section_body = (
        section_match.group(2).strip()
    )

    inline_subsection_match = (
        SUBSECTION_PATTERN.match(
            section_body
        )
    )

    # -------------------------------------------------
    # Section without inline subsection
    #
    # Example:
    #
    # 305.Whoever commits theft—
    # -------------------------------------------------

    if inline_subsection_match is None:

        section = {
            "number": section_number,
            "title": "",
            "text": (
                [section_body]
                if section_body
                else []
            ),
            "subsections": [],
            "illustrations": [],
            "supplementary": [],
        }

        return section, None

    # -------------------------------------------------
    # Section with inline subsection
    #
    # Example:
    #
    # 303.(1) Whoever...
    # -------------------------------------------------

    subsection_number = (
        f"("
        f"{inline_subsection_match.group(1)}"
        f")"
    )

    subsection_text = (
        inline_subsection_match
        .group(2)
        .strip()
    )

    subsection = {
        "number": subsection_number,
        "text": (
            [subsection_text]
            if subsection_text
            else []
        ),
        "clauses": [],
        "illustrations": [],
        "supplementary": [],
    }

    section = {
        "number": section_number,
        "title": "",
        "text": [],
        "subsections": [
            subsection
        ],
        "illustrations": [],
        "supplementary": [],
    }

    return section, subsection


def parse_bns() -> None:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: "
            f"{INPUT_FILE}"
        )

    print(
        "Reading extracted BNS text..."
    )

    text = INPUT_FILE.read_text(
        encoding="utf-8"
    )

    lines = text.splitlines()

    sections = []

    current_section = None
    current_subsection = None
    current_clause = None

    in_illustrations = False

    clause_style = None
    last_top_level_clause = None

    in_nested_clause_list = False
    nested_can_return_to_top_level = False

    # Points directly to either:
    #
    #     section["supplementary"]
    #
    # or:
    #
    #     subsection["supplementary"]
    #
    # while a supplementary legal block is active.
    supplementary_owner = None

    # =================================================
    # PARSING LOOP
    # =================================================

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        # -------------------------------------------------
        # Ignore extraction/control material
        # -------------------------------------------------

        if PAGE_MARKER_PATTERN.match(
            line
        ):
            continue

        if END_OF_ACT_PATTERN.match(
            line
        ):
            break

        if CHAPTER_PATTERN.match(
            line
        ):
            continue

        if OF_HEADING_PATTERN.match(
            line
        ):
            continue

        if UPPERCASE_HEADING_PATTERN.match(
            line
        ):
            continue

        # =================================================
        # SECTION
        # =================================================

        parsed_section = (
            parse_section_header(
                line
            )
        )

        if parsed_section is not None:

            (
                current_section,
                current_subsection,
            ) = parsed_section

            sections.append(
                current_section
            )

            current_clause = None

            in_illustrations = False

            clause_style = None
            last_top_level_clause = None

            in_nested_clause_list = False
            nested_can_return_to_top_level = False

            # A new section ends any previous
            # supplementary block.
            supplementary_owner = None

            continue

        if current_section is None:
            continue

        # =================================================
        # SUBSECTION
        # =================================================

        subsection_match = (
            SUBSECTION_PATTERN.match(
                line
            )
        )

        if subsection_match:

            candidate_number = (
                subsection_match.group(1)
            )

            # ---------------------------------------------
            # Genuine sequential subsection
            # ---------------------------------------------

            if should_start_new_subsection(
                candidate_number,
                current_subsection,
            ):

                current_subsection = {
                    "number": (
                        f"("
                        f"{candidate_number}"
                        f")"
                    ),
                    "text": [],
                    "clauses": [],
                    "illustrations": [],
                    "supplementary": [],
                }

                current_section[
                    "subsections"
                ].append(
                    current_subsection
                )

                current_clause = None

                in_illustrations = False

                clause_style = None
                last_top_level_clause = None

                in_nested_clause_list = False
                nested_can_return_to_top_level = False

                # A genuine new subsection ends
                # the previous supplementary block.
                supplementary_owner = None

                remainder = (
                    subsection_match
                    .group(2)
                    .strip()
                )

                if remainder:
                    current_subsection[
                        "text"
                    ].append(
                        remainder
                    )

                continue

            # ---------------------------------------------
            # Non-sequential numeric marker
            #
            # Example:
            #
            # "... sub-sections (4),
            # (6), (7) and (8) of section 331 ..."
            #
            # This is statutory text, NOT another
            # subsection.
            # ---------------------------------------------

            if supplementary_owner is not None:

                supplementary_owner.append(
                    line
                )

            elif in_illustrations:

                if current_subsection is not None:
                    current_subsection[
                        "illustrations"
                    ].append(
                        line
                    )

                else:
                    current_section[
                        "illustrations"
                    ].append(
                        line
                    )

            elif current_clause is not None:

                current_clause[
                    "text"
                ].append(
                    line
                )

            elif current_subsection is not None:

                current_subsection[
                    "text"
                ].append(
                    line
                )

            else:

                current_section[
                    "text"
                ].append(
                    line
                )

            continue

        # =================================================
               # =================================================
        # EXISTING ILLUSTRATIONS BLOCK
        # =================================================
        #
        # IMPORTANT:
        #
        # Illustration state must be checked BEFORE
        # supplementary markers such as "Explanation."
        #
        # Some statutory illustrations themselves contain
        # wording that looks like supplementary material.
        # While we are inside an Illustrations block, those
        # lines must remain illustrations.

        if in_illustrations:

            if current_subsection is not None:

                current_subsection[
                    "illustrations"
                ].append(
                    line
                )

            else:

                current_section[
                    "illustrations"
                ].append(
                    line
                )

            continue

        # =================================================
        # OPEN ILLUSTRATIONS BLOCK
        # =================================================

        (
            line_without_illustrations,
            opens_illustrations,
        ) = split_illustrations_marker(
            line
        )

        if opens_illustrations:

            # Preserve statutory text appearing before
            # "Illustrations." on the same line.

            if line_without_illustrations:

                if supplementary_owner is not None:

                    supplementary_owner.append(
                        line_without_illustrations
                    )

                elif current_clause is not None:

                    current_clause[
                        "text"
                    ].append(
                        line_without_illustrations
                    )

                elif current_subsection is not None:

                    current_subsection[
                        "text"
                    ].append(
                        line_without_illustrations
                    )

                else:

                    current_section[
                        "text"
                    ].append(
                        line_without_illustrations
                    )

            current_clause = None

            in_illustrations = True

            in_nested_clause_list = False
            nested_can_return_to_top_level = False

            # Illustrations are their own statutory block.
            supplementary_owner = None

            continue

        # =================================================
        # SUPPLEMENTARY LEGAL BLOCK
        # =================================================
        #
        # Examples:
        #
        # Explanation.—
        # Provided that...
        # Exception.—This section does not extend to—
        #
        # This occurs AFTER illustration handling so an
        # "Explanation." occurring inside an illustration
        # is not misclassified.

        detected_scope = supplementary_scope(
            line
        )

        if detected_scope is not None:

            current_clause = None

            in_nested_clause_list = False
            nested_can_return_to_top_level = False

            if (
                detected_scope == "section"
                or current_subsection is None
            ):

                supplementary_owner = (
                    current_section[
                        "supplementary"
                    ]
                )

            else:

                supplementary_owner = (
                    current_subsection[
                        "supplementary"
                    ]
                )

            supplementary_owner.append(
                line
            )

            continue

        # -------------------------------------------------
        # Continue existing supplementary block
        # -------------------------------------------------

        if supplementary_owner is not None:

            supplementary_owner.append(
                line
            )

            continue

        # =================================================
        # CLAUSE
        # =================================================

        clause_match = CLAUSE_PATTERN.match(
            line
        )

        if (
            clause_match
            and current_subsection is not None
        ):

            candidate_label = (
                clause_match.group(1)
            )

            # ---------------------------------------------
            # Currently inside a nested clause list
            #
            # Example:
            #
            # (a) ...
            #     (i) ...
            #     (ii) ...
            # (b) ...
            # ---------------------------------------------

            if in_nested_clause_list:

                if should_exit_nested_clause_list(
                    candidate_label,
                    clause_style,
                    last_top_level_clause,
                    nested_can_return_to_top_level,
                ):

                    in_nested_clause_list = False
                    nested_can_return_to_top_level = False

                else:

                    if current_clause is not None:

                        current_clause[
                            "text"
                        ].append(
                            line
                        )

                    else:

                        current_subsection[
                            "text"
                        ].append(
                            line
                        )

                    continue

            # ---------------------------------------------
            # Determine whether candidate is a genuine
            # top-level clause.
            # ---------------------------------------------

            (
                is_top_level,
                resolved_style,
            ) = should_start_new_clause(
                candidate_label,
                clause_style,
                last_top_level_clause,
            )

            # ---------------------------------------------
            # Nested / restarted list
            # ---------------------------------------------

            if not is_top_level:

                nested_style = (
                    infer_clause_style(
                        candidate_label
                    )
                )

                in_nested_clause_list = True

                # A nested list using a DIFFERENT style
                # may later return to the parent sequence.
                #
                # Example:
                #
                # (a)
                #     (i)
                #     (ii)
                # (b)
                #
                # A restarted SAME-style list stays nested.
                #
                # Example:
                #
                # (i)
                # (ii)
                # Provided that—
                #     (i)
                #     (ii)
                #     (iii)

                nested_can_return_to_top_level = (
                    clause_style is not None
                    and nested_style
                    != clause_style
                )

                if current_clause is not None:

                    current_clause[
                        "text"
                    ].append(
                        line
                    )

                else:

                    current_subsection[
                        "text"
                    ].append(
                        line
                    )

                continue

            # ---------------------------------------------
            # Genuine top-level Clause
            # ---------------------------------------------

            clause_style = (
                resolved_style
            )

            last_top_level_clause = (
                candidate_label
            )

            in_nested_clause_list = False
            nested_can_return_to_top_level = False

            current_clause = {
                "number": (
                    f"("
                    f"{candidate_label}"
                    f")"
                ),
                "text": [],
            }

            current_subsection[
                "clauses"
            ].append(
                current_clause
            )

            remainder = (
                clause_match
                .group(2)
                .strip()
            )

            if remainder:

                current_clause[
                    "text"
                ].append(
                    remainder
                )

            continue

        # =================================================
        # NORMAL CONTINUATION TEXT
        # =================================================

        if current_subsection is not None:

            if current_clause is not None:

                current_clause[
                    "text"
                ].append(
                    line
                )

            else:

                current_subsection[
                    "text"
                ].append(
                    line
                )

        else:

            current_section[
                "text"
            ].append(
                line
            )

    # =====================================================
    # COUNTS
    # =====================================================

    print(
        f"Sections detected: "
        f"{len(sections)}"
    )

    subsection_count = sum(
        len(
            section["subsections"]
        )
        for section in sections
    )

    clause_count = sum(
        len(
            subsection["clauses"]
        )
        for section in sections
        for subsection
        in section["subsections"]
    )

    illustration_count = sum(
        len(
            section["illustrations"]
        )
        + sum(
            len(
                subsection["illustrations"]
            )
            for subsection
            in section["subsections"]
        )
        for section in sections
    )

    supplementary_count = sum(
        len(
            section["supplementary"]
        )
        + sum(
            len(
                subsection["supplementary"]
            )
            for subsection
            in section["subsections"]
        )
        for section in sections
    )

    print(
        f"Subsections detected: "
        f"{subsection_count}"
    )

    print(
        f"Clauses detected: "
        f"{clause_count}"
    )

    print(
        f"Illustration lines detected: "
        f"{illustration_count}"
    )

    print(
        f"Supplementary lines detected: "
        f"{supplementary_count}"
    )

    # =====================================================
    # EXPORT bns_parsed.txt
    # =====================================================

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as output:

        for section in sections:

            # ---------------------------------------------
            # Section header
            # ---------------------------------------------

            output.write(
                "\n"
                f"===== SECTION "
                f"{section['number']} "
                "=====\n"
            )

            output.write(
                f"TITLE: "
                f"{section['title']}\n"
            )

            # ---------------------------------------------
            # Section statutory text
            # ---------------------------------------------

            if section["text"]:

                output.write(
                    "\nSECTION TEXT:\n"
                )

                output.write(
                    "\n".join(
                        section["text"]
                    )
                )

                output.write(
                    "\n"
                )

            # ---------------------------------------------
            # Section illustrations
            # ---------------------------------------------

            if section["illustrations"]:

                output.write(
                    "\nILLUSTRATIONS:\n"
                )

                output.write(
                    "\n".join(
                        section[
                            "illustrations"
                        ]
                    )
                )

                output.write(
                    "\n"
                )

            # =============================================
            # SUBSECTIONS
            # =============================================

            for subsection in section[
                "subsections"
            ]:

                output.write(
                    "\n"
                    f"--- SUBSECTION "
                    f"{subsection['number']} "
                    "---\n"
                )

                # -----------------------------------------
                # Subsection statutory text
                # -----------------------------------------

                if subsection["text"]:

                    output.write(
                        "\n".join(
                            subsection[
                                "text"
                            ]
                        )
                    )

                    output.write(
                        "\n"
                    )

                # -----------------------------------------
                # Clauses
                # -----------------------------------------

                for clause in subsection[
                    "clauses"
                ]:

                    output.write(
                        "\n"
                        f"CLAUSE "
                        f"{clause['number']}:\n"
                    )

                    output.write(
                        "\n".join(
                            clause["text"]
                        )
                    )

                    output.write(
                        "\n"
                    )

                # -----------------------------------------
                # Subsection illustrations
                # -----------------------------------------

                if subsection[
                    "illustrations"
                ]:

                    output.write(
                        "\nILLUSTRATIONS:\n"
                    )

                    output.write(
                        "\n".join(
                            subsection[
                                "illustrations"
                            ]
                        )
                    )

                    output.write(
                        "\n"
                    )

                # -----------------------------------------
                # Subsection supplementary material
                #
                # Examples:
                #
                # Explanation.
                # Provided that...
                # -----------------------------------------

                if subsection[
                    "supplementary"
                ]:

                    output.write(
                        "\n"
                        "SUBSECTION SUPPLEMENTARY:"
                        "\n"
                    )

                    output.write(
                        "\n".join(
                            subsection[
                                "supplementary"
                            ]
                        )
                    )

                    output.write(
                        "\n"
                    )

            # ---------------------------------------------
            # Section supplementary material
            #
            # Kept after its subsections because section-
            # wide Exceptions commonly appear after the
            # operative subsection/clauses.
            #
            # Example:
            #
            # Exception.—This section does not extend to—
            # ---------------------------------------------

            if section[
                "supplementary"
            ]:

                output.write(
                    "\n"
                    "SECTION SUPPLEMENTARY:"
                    "\n"
                )

                output.write(
                    "\n".join(
                        section[
                            "supplementary"
                        ]
                    )
                )

                output.write(
                    "\n"
                )

    print(
        "\nBNS parsing completed."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    parse_bns()