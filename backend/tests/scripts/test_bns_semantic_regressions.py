from scripts.ingest_bns_structure import (
    parse_sections,
)


def get_section(
    sections,
    section_number: str,
):
    for section in sections:
        if (
            section["number"]
            == section_number
        ):
            return section

    raise AssertionError(
        f"Section {section_number} "
        "was not found."
    )


def get_subsection(
    section,
    subsection_number: str,
):
    for subsection in section[
        "subsections"
    ]:
        if (
            subsection["number"]
            == subsection_number
        ):
            return subsection

    raise AssertionError(
        f"Subsection {subsection_number} "
        f"was not found in Section "
        f"{section['number']}."
    )


def flatten_subsection(
    subsection,
) -> str:

    lines = []

    lines.extend(
        subsection["text"]
    )

    lines.extend(
        subsection.get(
            "supplementary",
            [],
        )
    )

    lines.extend(
        subsection.get(
            "illustrations",
            [],
        )
    )

    for clause in subsection[
        "clauses"
    ]:
        lines.extend(
            clause["text"]
        )

    return " ".join(
        lines
    ).lower()


def flatten_section(
    section,
) -> str:

    lines = []

    lines.extend(
        section["text"]
    )

    lines.extend(
        section.get(
            "supplementary",
            [],
        )
    )

    lines.extend(
        section.get(
            "illustrations",
            [],
        )
    )

    for subsection in section[
        "subsections"
    ]:
        lines.append(
            flatten_subsection(
                subsection
            )
        )

    return " ".join(
        lines
    ).lower()


def test_section_303_2_generic_theft_punishment_regression():
    """
    Regression for the original NyayaAI theft bug.

    Generic theft under BNS Section 303(2)
    must not inherit the ten-year punishment
    from another theft-related provision.
    """

    sections = parse_sections()

    section_303 = get_section(
        sections,
        "303",
    )

    subsection_2 = get_subsection(
        section_303,
        "(2)",
    )

    text = flatten_subsection(
        subsection_2
    )

    # Ordinary theft.
    assert "three years" in text
    assert "fine" in text
    assert "or with both" in text

    # Second/subsequent conviction.
    assert "second or subsequent conviction" in text
    assert "one year" in text
    assert "five years" in text

    # First-time low-value theft proviso.
    assert "five thousand rupees" in text
    assert "community service" in text

    # Critical regression guard:
    # generic theft must never silently become
    # the old ten-year result again.
    assert "ten years" not in text


def test_section_304_is_snatching_not_extortion_regression():
    """
    Section 304 must remain the BNS snatching
    provision and must not absorb the old
    extortion hierarchy/content.
    """

    sections = parse_sections()

    section_304 = get_section(
        sections,
        "304",
    )

    text = flatten_section(
        section_304
    )

    assert "snatching" in text

    # Regression guard against the corrupted
    # old Section 304 hierarchy.
    assert "extortion" not in text