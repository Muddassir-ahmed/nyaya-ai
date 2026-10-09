from scripts.extract_bns_text import (
    rebuild_page_lines,
    should_keep_fragment,
)


def test_main_body_fragment_is_kept():
    assert (
        should_keep_fragment(
            x=245.08,
            y=215.35,
        )
        is True
    )


def test_left_margin_heading_is_removed():
    assert (
        should_keep_fragment(
            x=120.08,
            y=338.85,
        )
        is False
    )


def test_right_margin_heading_is_removed():
    assert (
        should_keep_fragment(
            x=1014.58,
            y=1076.35,
        )
        is False
    )


def test_gazette_header_is_removed():
    assert (
        should_keep_fragment(
            x=452.04,
            y=146.40,
        )
        is False
    )


def test_duplicate_zero_coordinate_text_is_removed():
    assert (
        should_keep_fragment(
            x=0.0,
            y=0.0,
        )
        is False
    )


def test_split_section_heading_is_rebuilt():
    fragments = [
        (
            190.35,
            295.08,
            0,
            "304.",
        ),
        (
            190.35,
            295.08,
            1,
            "(",
        ),
        (
            190.35,
            295.08,
            2,
            "1",
        ),
        (
            190.35,
            295.08,
            3,
            ") Theft is snatching",
        ),
    ]

    assert (
        rebuild_page_lines(
            fragments
        )
        == "304.(1) Theft is snatching"
    )


def test_split_non_subsection_heading_is_rebuilt():
    fragments = [
        (
            340.35,
            295.08,
            0,
            "305",
        ),
        (
            340.35,
            295.08,
            1,
            ".",
        ),
        (
            340.35,
            295.08,
            2,
            "Whoever commits theft—",
        ),
    ]

    assert (
        rebuild_page_lines(
            fragments
        )
        == "305.Whoever commits theft—"
    )