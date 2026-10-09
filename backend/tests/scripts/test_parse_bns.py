import pytest

from scripts.parse_bns import (
    CHAPTER_PATTERN,
    END_OF_ACT_PATTERN,
    OF_HEADING_PATTERN,
    PAGE_MARKER_PATTERN,
    SECTION_PATTERN,
    UPPERCASE_HEADING_PATTERN,
    parse_section_header,
    should_start_new_clause,
    should_start_new_subsection,
    split_illustrations_marker,
    should_exit_nested_clause_list,
    supplementary_scope,
)


@pytest.mark.parametrize(
    ("text", "number"),
    [
        (
            "303.(1) Whoever, intending to take dishonestly...",
            "303",
        ),
        (
            "304. (1) Theft is snatching if...",
            "304",
        ),
        (
            "305.Whoever commits theft—",
            "305",
        ),
        (
            "306.Whoever, being a clerk or servant...",
            "306",
        ),
        (
            "307.Whoever commits theft, having made preparation...",
            "307",
        ),
        (
            "308.(1) Whoever intentionally puts any person...",
            "308",
        ),
        (
            "309.(1) In all robbery there is either theft or extortion.",
            "309",
        ),
        (
            "310. (1) When five or more persons conjointly...",
            "310",
        ),
    ],
)
def test_section_pattern_accepts_bns_boundary_formats(
    text: str,
    number: str,
):
    match = SECTION_PATTERN.match(text)

    assert match is not None
    assert match.group(1) == number
    assert match.group(2).strip()


def test_section_pattern_does_not_match_subsections():
    assert (
        SECTION_PATTERN.match(
            "(2) Whoever commits snatching..."
        )
        is None
    )


def test_section_pattern_does_not_match_clauses():
    assert (
        SECTION_PATTERN.match(
            "(a) in any building or vessel..."
        )
        is None
    )


def test_section_pattern_rejects_pdf_signature_metadata():
    assert (
        SECTION_PATTERN.match(
            "2.5.4.20=e8b886a9336825f4d"
        )
        is None
    )


def test_section_pattern_accepts_section_2_without_space():
    match = SECTION_PATTERN.match(
        "2.In this Sanhita, unless the context otherwise requires,––"
    )

    assert match is not None
    assert match.group(1) == "2"


def test_inline_subsection_1_is_not_used_as_section_title():
    parsed = parse_section_header(
        "303.(1) Whoever, intending to take dishonestly any movable property"
    )

    assert parsed is not None

    section, subsection = parsed

    assert section["number"] == "303"
    assert section["title"] == ""

    assert len(
        section["subsections"]
    ) == 1

    assert subsection is not None
    assert subsection["number"] == "(1)"

    assert subsection["text"][0].startswith(
        "Whoever, intending to take dishonestly"
    )


def test_inline_subsection_with_space_is_detected():
    parsed = parse_section_header(
        "304. (1) Theft is snatching if, in order to commit theft"
    )

    assert parsed is not None

    section, subsection = parsed

    assert section["number"] == "304"
    assert section["title"] == ""

    assert subsection is not None
    assert subsection["number"] == "(1)"

    assert subsection["text"][0].startswith(
        "Theft is snatching"
    )


def test_section_without_inline_subsection_keeps_body_as_section_text():
    parsed = parse_section_header(
        "305.Whoever commits theft—"
    )

    assert parsed is not None

    section, subsection = parsed

    assert section["number"] == "305"
    assert section["title"] == ""

    assert section["text"] == [
        "Whoever commits theft—"
    ]

    assert section["subsections"] == []
    assert subsection is None


def test_illustrations_marker_is_detected():
    text, is_illustrations = (
        split_illustrations_marker(
            "The provision applies. Illustrations."
        )
    )

    assert is_illustrations is True
    assert text == "The provision applies."


def test_standalone_illustrations_marker_is_detected():
    text, is_illustrations = (
        split_illustrations_marker(
            "Illustrations."
        )
    )

    assert is_illustrations is True
    assert text == ""


def test_word_illustration_is_not_marker():
    text, is_illustrations = (
        split_illustrations_marker(
            "Every Illustration is subject to the exception."
        )
    )

    assert is_illustrations is False

    assert (
        text
        == "Every Illustration is subject to the exception."
    )


def test_page_marker_is_detected():
    assert PAGE_MARKER_PATTERN.match(
        "===== PAGE 81 ====="
    )


def test_end_of_act_separator_is_detected():
    assert END_OF_ACT_PATTERN.match(
        "— — —— —"
    )


def test_chapter_heading_is_detected():
    assert CHAPTER_PATTERN.match(
        "CHAPTER XX"
    )


def test_of_heading_is_detected():
    assert OF_HEADING_PATTERN.match(
        "Of robbery and dacoity"
    )


def test_uppercase_heading_is_detected():
    assert UPPERCASE_HEADING_PATTERN.match(
        "REPEAL AND SAVINGS"
    )


def test_normal_legal_sentence_is_not_uppercase_heading():
    assert (
        UPPERCASE_HEADING_PATTERN.match(
            "Whoever commits theft shall be punished."
        )
        is None
    )


def test_standalone_singular_illustration_is_detected():
    text, is_illustrations = (
        split_illustrations_marker(
            "Illustration."
        )
    )

    assert is_illustrations is True
    assert text == ""


def test_singular_illustration_word_inside_sentence_is_not_marker():
    text, is_illustrations = (
        split_illustrations_marker(
            "The Court considered an Illustration."
        )
    )

    assert is_illustrations is False

    assert (
        text
        == "The Court considered an Illustration."
    )


def test_nonsequential_subsection_marker_is_not_new_subsection():
    current = {
        "number": "(28)"
    }

    assert (
        should_start_new_subsection(
            "3",
            current,
        )
        is False
    )


def test_sequential_subsection_marker_is_new_subsection():
    current = {
        "number": "(28)"
    }

    assert (
        should_start_new_subsection(
            "29",
            current,
        )
        is True
    )


def test_alpha_clause_list_rejects_nested_roman_i():
    is_top_level, style = (
        should_start_new_clause(
            "a",
            None,
            None,
        )
    )

    assert is_top_level is True
    assert style == "alpha"

    is_top_level, style = (
        should_start_new_clause(
            "i",
            style,
            "a",
        )
    )

    assert is_top_level is False


def test_alpha_clause_list_accepts_next_letter():
    is_top_level, style = (
        should_start_new_clause(
            "b",
            "alpha",
            "a",
        )
    )

    assert is_top_level is True
    assert style == "alpha"


def test_roman_clause_list_accepts_next_roman():
    is_top_level, style = (
        should_start_new_clause(
            "i",
            None,
            None,
        )
    )

    assert is_top_level is True
    assert style == "roman"

    is_top_level, style = (
        should_start_new_clause(
            "ii",
            style,
            "i",
        )
    )

    assert is_top_level is True


def test_roman_clause_list_rejects_restart():
    is_top_level, style = (
        should_start_new_clause(
            "i",
            "roman",
            "ii",
        )
    )

    assert is_top_level is False

def test_different_style_nested_list_can_return_to_parent():
    assert (
        should_exit_nested_clause_list(
            "b",
            "alpha",
            "a",
            True,
        )
        is True
    )


def test_same_style_restarted_list_stays_nested():
    # Section 78-style structure:
    #
    # top-level (i), (ii)
    # Provided that—
    # nested (i), (ii), (iii)
    #
    # The nested (iii) must NOT become another
    # top-level Clause.
    assert (
        should_exit_nested_clause_list(
            "iii",
            "roman",
            "ii",
            False,
        )
        is False
    )

def test_explanation_is_subsection_supplementary():
    assert (
        supplementary_scope(
            "Explanation.—For the purposes "
            "of this sub-section,—"
        )
        == "subsection"
    )


def test_provided_that_is_subsection_supplementary():
    assert (
        supplementary_scope(
            "Provided that such conduct "
            "shall not amount to stalking if—"
        )
        == "subsection"
    )


def test_section_exception_is_section_supplementary():
    assert (
        supplementary_scope(
            "Exception.—This section does "
            "not extend to—"
        )
        == "section"
    )


def test_normal_sentence_is_not_supplementary():
    assert (
        supplementary_scope(
            "Whoever commits theft "
            "shall be punished."
        )
        is None
    )
