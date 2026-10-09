from types import SimpleNamespace

import pytest

from scripts.create_bns_chunks import (
    MAX_CHARS,
    add_chunks,
    split_parent_text,
    validate_new_chunks,
    validate_sections_for_chunking,
)


def test_split_parent_text_separates_illustrations():
    body, illustrations = split_parent_text(
        "Main legal text.\n\n"
        "Illustrations.\n"
        "(a) First example."
    )

    assert body == "Main legal text."
    assert illustrations == "(a) First example."


def test_split_parent_text_without_illustrations():
    body, illustrations = split_parent_text(
        "Main legal text."
    )

    assert body == "Main legal text."
    assert illustrations == ""


def test_add_chunks_repeats_header():
    chunks = []

    add_chunks(
        chunks,
        document_id=2,
        act_id=1,
        version_id=1,
        section_id=303,
        subsection_id=1,
        clause_id=None,
        header=(
            "Section 303\n"
            "Subsection (1)"
        ),
        body=(
            "legalword " * 1000
        ),
    )

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk["content"].startswith(
            "Section 303\n"
            "Subsection (1)\n\n"
        )

        assert (
            len(chunk["content"])
            <= MAX_CHARS
        )


def test_validate_sections_accepts_1_to_358():
    sections = [
        SimpleNamespace(
            section_number=str(number)
        )
        for number in range(
            1,
            359,
        )
    ]

    validate_sections_for_chunking(
        sections
    )


def test_validate_sections_rejects_missing_section():
    sections = [
        SimpleNamespace(
            section_number=str(number)
        )
        for number in range(
            1,
            358,
        )
    ]

    with pytest.raises(
        RuntimeError
    ):
        validate_sections_for_chunking(
            sections
        )


def test_validate_new_chunks_rejects_duplicate_content():
    chunks = []

    add_chunks(
        chunks,
        document_id=2,
        act_id=1,
        version_id=1,
        section_id=1,
        subsection_id=None,
        clause_id=None,
        header="Section 1",
        body="Same content.",
    )

    duplicate = dict(
        chunks[0]
    )

    chunks.append(
        duplicate
    )

    with pytest.raises(
        RuntimeError
    ):
        validate_new_chunks(
            chunks
        )