import pytest

from scripts.ingest_bns_structure import (
    build_parent_text,
    parse_sections,
    validate_sections_for_ingestion,
)


def test_section_text_marker_is_not_content(
    tmp_path,
):
    parsed_file = (
        tmp_path
        / "bns_parsed.txt"
    )

    parsed_file.write_text(
        """
===== SECTION 305 =====
TITLE:

SECTION TEXT:
Whoever commits theft—
(a) in any building.
""".strip(),
        encoding="utf-8",
    )

    sections = parse_sections(
        parsed_file
    )

    assert len(sections) == 1

    section = sections[0]

    assert section["number"] == "305"
    assert section["title"] == ""

    assert section["text"] == [
        "Whoever commits theft—",
        "(a) in any building.",
    ]

    assert (
        "SECTION TEXT:"
        not in section["text"]
    )


def test_subsection_illustrations_do_not_become_clauses(
    tmp_path,
):
    parsed_file = (
        tmp_path
        / "bns_parsed.txt"
    )

    parsed_file.write_text(
        """
===== SECTION 100 =====
TITLE:

--- SUBSECTION (1) ---
Main provision.

CLAUSE (a):
Real statutory clause.

ILLUSTRATIONS:
(a) First illustration.
(b) Second illustration.
""".strip(),
        encoding="utf-8",
    )

    sections = parse_sections(
        parsed_file
    )

    subsection = (
        sections[0]["subsections"][0]
    )

    assert len(
        subsection["clauses"]
    ) == 1

    assert (
        subsection["clauses"][0][
            "number"
        ]
        == "(a)"
    )

    assert (
        subsection["clauses"][0][
            "text"
        ]
        == [
            "Real statutory clause."
        ]
    )

    assert (
        subsection["illustrations"]
        == [
            "(a) First illustration.",
            "(b) Second illustration.",
        ]
    )


def test_section_level_illustrations_are_preserved(
    tmp_path,
):
    parsed_file = (
        tmp_path
        / "bns_parsed.txt"
    )

    parsed_file.write_text(
        """
===== SECTION 200 =====
TITLE:

SECTION TEXT:
Main section text.

ILLUSTRATIONS:
(a) Section example.
(b) Another example.
""".strip(),
        encoding="utf-8",
    )

    sections = parse_sections(
        parsed_file
    )

    section = sections[0]

    assert section["text"] == [
        "Main section text."
    ]

    assert section["illustrations"] == [
        "(a) Section example.",
        "(b) Another example.",
    ]


def test_build_parent_text_preserves_illustrations():
    text = build_parent_text(
        [
            "Main statutory text."
        ],
        [
            "(a) First example.",
            "(b) Second example.",
        ],
    )

    assert (
        "Main statutory text."
        in text
    )

    assert "Illustrations." in text

    assert (
        "(a) First example."
        in text
    )

    assert (
        "(b) Second example."
        in text
    )


def test_validate_sections_accepts_1_to_358():
    sections = [
        {
            "number": str(number)
        }
        for number in range(
            1,
            359,
        )
    ]

    validate_sections_for_ingestion(
        sections
    )


def test_validate_sections_rejects_missing_section():
    sections = [
        {
            "number": str(number)
        }
        for number in range(
            1,
            358,
        )
    ]

    with pytest.raises(
        RuntimeError
    ):
        validate_sections_for_ingestion(
            sections
        )