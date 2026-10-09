from pathlib import Path

from scripts.parse_bns import (
    CLAUSE_PATTERN,
    SECTION_PATTERN,
    SUBSECTION_PATTERN,
    parse_section_header,
    should_start_new_clause,
    should_start_new_subsection,
    split_illustrations_marker,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette_clean.txt"
)


def main():
    lines = INPUT_FILE.read_text(
        encoding="utf-8"
    ).splitlines()

    current_section = None
    current_subsection = None

    clause_style = None
    last_top_level_clause = None

    in_illustrations = False

    rejected_subsections = []
    rejected_clauses = []

    previous_nonempty = ""

    for line_number, raw_line in enumerate(
        lines,
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        # -----------------------------------------
        # Section
        # -----------------------------------------

        section_match = SECTION_PATTERN.match(
            line
        )

        if section_match:
            current_section = (
                section_match.group(1)
            )

            current_subsection = None
            clause_style = None
            last_top_level_clause = None
            in_illustrations = False

            previous_nonempty = line
            continue

        # Handle section headers such as:
        # 303.(1) Whoever...
        parsed_section = parse_section_header(
            line
        )

        if parsed_section is not None:
            section, inline_subsection = (
                parsed_section
            )

            current_section = section[
                "number"
            ]

            current_subsection = (
                inline_subsection
            )

            clause_style = None
            last_top_level_clause = None
            in_illustrations = False

            previous_nonempty = line
            continue

        if current_section is None:
            previous_nonempty = line
            continue

        # -----------------------------------------
        # Subsection candidates
        # -----------------------------------------

        subsection_match = (
            SUBSECTION_PATTERN.match(
                line
            )
        )

        if subsection_match:
            candidate_number = (
                subsection_match.group(1)
            )

            if should_start_new_subsection(
                candidate_number,
                current_subsection,
            ):
                current_subsection = {
                    "number": (
                        f"({candidate_number})"
                    )
                }

                clause_style = None
                last_top_level_clause = None
                in_illustrations = False

            else:
                rejected_subsections.append(
                    {
                        "line": line_number,
                        "section": current_section,
                        "current_subsection": (
                            current_subsection[
                                "number"
                            ]
                            if current_subsection
                            else None
                        ),
                        "candidate": (
                            f"({candidate_number})"
                        ),
                        "previous": (
                            previous_nonempty
                        ),
                        "text": line,
                    }
                )

            previous_nonempty = line
            continue

        # -----------------------------------------
        # Illustration state
        # -----------------------------------------

        _, starts_illustrations = (
            split_illustrations_marker(
                line
            )
        )

        if starts_illustrations:
            in_illustrations = True
            previous_nonempty = line
            continue

        if in_illustrations:
            previous_nonempty = line
            continue

        # -----------------------------------------
        # Clause candidates
        # -----------------------------------------

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

            (
                accepted,
                resolved_style,
            ) = should_start_new_clause(
                candidate_label,
                clause_style,
                last_top_level_clause,
            )

            if accepted:
                clause_style = (
                    resolved_style
                )

                last_top_level_clause = (
                    candidate_label
                )

            else:
                rejected_clauses.append(
                    {
                        "line": line_number,
                        "section": current_section,
                        "subsection": (
                            current_subsection[
                                "number"
                            ]
                        ),
                        "style": clause_style,
                        "last_top_level": (
                            last_top_level_clause
                        ),
                        "candidate": (
                            f"({candidate_label})"
                        ),
                        "previous": (
                            previous_nonempty
                        ),
                        "text": line,
                    }
                )

        previous_nonempty = line

    print("=" * 80)
    print("REJECTED SUBSECTION CANDIDATES")
    print("=" * 80)

    for item in rejected_subsections:
        print()
        print(
            f"Line {item['line']} | "
            f"Section {item['section']} | "
            f"current={item['current_subsection']} | "
            f"candidate={item['candidate']}"
        )
        print(
            f"PREVIOUS: {item['previous']}"
        )
        print(
            f"LINE    : {item['text']}"
        )

    print()
    print(
        "Rejected subsection candidates:",
        len(rejected_subsections),
    )

    print()
    print("=" * 80)
    print("REJECTED CLAUSE CANDIDATES")
    print("=" * 80)

    for item in rejected_clauses:
        print()
        print(
            f"Line {item['line']} | "
            f"Section {item['section']} "
            f"{item['subsection']} | "
            f"style={item['style']} | "
            f"last={item['last_top_level']} | "
            f"candidate={item['candidate']}"
        )
        print(
            f"PREVIOUS: {item['previous']}"
        )
        print(
            f"LINE    : {item['text']}"
        )

    print()
    print(
        "Rejected clause candidates:",
        len(rejected_clauses),
    )


if __name__ == "__main__":
    main()