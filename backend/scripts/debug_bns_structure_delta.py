from collections import Counter, defaultdict
from pathlib import Path

from scripts.ingest_bns_structure import (
    parse_sections,
)
from scripts.parse_bns import (
    CLAUSE_PATTERN,
    END_OF_ACT_PATTERN,
    PAGE_MARKER_PATTERN,
    SUBSECTION_PATTERN,
    parse_section_header,
    split_illustrations_marker,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEAN_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette_clean.txt"
)


def collect_legacy_structure():
    """
    Reproduce the old permissive structural behavior:

    - every subsection-looking marker becomes a
      subsection;
    - every clause-looking marker becomes a Clause;
    - illustration blocks still suppress clause
      parsing exactly as before.

    This is diagnostic only.
    """

    lines = CLEAN_FILE.read_text(
        encoding="utf-8"
    ).splitlines()

    subsection_occurrences = []
    clause_occurrences = []

    subsection_context = defaultdict(
        list
    )
    clause_context = defaultdict(
        list
    )

    current_section = None
    current_subsection = None

    in_illustrations = False

    previous_nonempty = ""

    for line_number, raw_line in enumerate(
        lines,
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        if PAGE_MARKER_PATTERN.match(
            line
        ):
            continue

        if END_OF_ACT_PATTERN.match(
            line
        ):
            break

        parsed_section = (
            parse_section_header(
                line
            )
        )

        if parsed_section is not None:
            (
                section,
                inline_subsection,
            ) = parsed_section

            current_section = (
                section["number"]
            )

            current_subsection = None
            in_illustrations = False

            if (
                inline_subsection
                is not None
            ):
                current_subsection = (
                    inline_subsection[
                        "number"
                    ]
                )

                key = (
                    current_section,
                    current_subsection,
                )

                subsection_occurrences.append(
                    key
                )

                subsection_context[
                    key
                ].append(
                    (
                        line_number,
                        previous_nonempty,
                        line,
                    )
                )

            previous_nonempty = line
            continue

        if current_section is None:
            previous_nonempty = line
            continue

        subsection_match = (
            SUBSECTION_PATTERN.match(
                line
            )
        )

        if subsection_match:
            current_subsection = (
                f"("
                f"{subsection_match.group(1)}"
                f")"
            )

            key = (
                current_section,
                current_subsection,
            )

            subsection_occurrences.append(
                key
            )

            subsection_context[
                key
            ].append(
                (
                    line_number,
                    previous_nonempty,
                    line,
                )
            )

            in_illustrations = False

            previous_nonempty = line
            continue

        # This ordering intentionally mirrors the
        # original parser behavior.
        if in_illustrations:
            previous_nonempty = line
            continue

        (
            _,
            starts_illustrations,
        ) = split_illustrations_marker(
            line
        )

        if starts_illustrations:
            in_illustrations = True

            previous_nonempty = line
            continue

        clause_match = (
            CLAUSE_PATTERN.match(
                line
            )
        )

        if (
            clause_match
            and current_subsection
            is not None
        ):
            clause_number = (
                f"("
                f"{clause_match.group(1)}"
                f")"
            )

            key = (
                current_section,
                current_subsection,
                clause_number,
            )

            clause_occurrences.append(
                key
            )

            clause_context[
                key
            ].append(
                (
                    line_number,
                    previous_nonempty,
                    line,
                )
            )

        previous_nonempty = line

    return (
        subsection_occurrences,
        clause_occurrences,
        subsection_context,
        clause_context,
    )


def collect_current_structure():
    sections = parse_sections()

    subsection_occurrences = []
    clause_occurrences = []

    for section in sections:
        section_number = (
            section["number"]
        )

        for subsection in section[
            "subsections"
        ]:
            subsection_number = (
                subsection["number"]
            )

            subsection_occurrences.append(
                (
                    section_number,
                    subsection_number,
                )
            )

            for clause in subsection[
                "clauses"
            ]:
                clause_occurrences.append(
                    (
                        section_number,
                        subsection_number,
                        clause["number"],
                    )
                )

    return (
        subsection_occurrences,
        clause_occurrences,
    )


def main():
    (
        legacy_subsections,
        legacy_clauses,
        subsection_context,
        clause_context,
    ) = collect_legacy_structure()

    (
        current_subsections,
        current_clauses,
    ) = collect_current_structure()

    legacy_subsection_set = set(
        legacy_subsections
    )

    current_subsection_set = set(
        current_subsections
    )

    legacy_clause_set = set(
        legacy_clauses
    )

    current_clause_set = set(
        current_clauses
    )

    print("=" * 80)
    print("STRUCTURE DELTA")
    print("=" * 80)

    print()
    print(
        "Legacy subsection occurrences:",
        len(legacy_subsections),
    )

    print(
        "Legacy unique subsection keys:",
        len(legacy_subsection_set),
    )

    print(
        "Current subsection occurrences:",
        len(current_subsections),
    )

    print(
        "Current unique subsection keys:",
        len(current_subsection_set),
    )

    print()
    print(
        "Legacy clause occurrences:",
        len(legacy_clauses),
    )

    print(
        "Legacy unique clause keys:",
        len(legacy_clause_set),
    )

    print(
        "Current clause occurrences:",
        len(current_clauses),
    )

    print(
        "Current unique clause keys:",
        len(current_clause_set),
    )

    lost_subsections = sorted(
        legacy_subsection_set
        - current_subsection_set,
        key=lambda key: (
            int(key[0]),
            key[1],
        ),
    )

    lost_clauses = sorted(
        legacy_clause_set
        - current_clause_set,
        key=lambda key: (
            int(key[0]),
            key[1],
            key[2],
        ),
    )

    print()
    print("=" * 80)
    print("UNIQUE SUBSECTION KEYS REMOVED")
    print("=" * 80)

    if not lost_subsections:
        print("None")

    for key in lost_subsections:
        print()
        print(
            "KEY:",
            key,
        )

        for (
            line_number,
            previous,
            line,
        ) in subsection_context[key]:

            print(
                f"Line {line_number}"
            )

            print(
                "PREVIOUS:",
                previous,
            )

            print(
                "LINE    :",
                line,
            )

    print()
    print("=" * 80)
    print("UNIQUE CLAUSE KEYS REMOVED")
    print("=" * 80)

    if not lost_clauses:
        print("None")

    for key in lost_clauses:
        print()
        print(
            "KEY:",
            key,
        )

        for (
            line_number,
            previous,
            line,
        ) in clause_context[key]:

            print(
                f"Line {line_number}"
            )

            print(
                "PREVIOUS:",
                previous,
            )

            print(
                "LINE    :",
                line,
            )

        print(
            "Legacy occurrence count:",
            Counter(
                legacy_clauses
            )[key],
        )


if __name__ == "__main__":
    main()