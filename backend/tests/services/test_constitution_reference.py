import pytest

from app.services.constitution_reference import (
    extract_article_reference,
    normalize_article_identifier,
)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "What does Article 21 of the Constitution of India say?",
            "21",
        ),
        ("Explain Article 21A of the Constitution.", "21A"),
        ("What is Article 239AA?", "239AA"),
        ("Explain Article 243-I.", "243-I"),
        ("Explain Article 243Z-I.", "243Z-I"),
    ],
)
def test_extract_article_reference_stops_at_identifier(
    query: str,
    expected: str,
) -> None:
    assert extract_article_reference(query) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("21", "21"),
        ("21A", "21A"),
        ("239AA", "239AA"),
        ("243-I", "243I"),
        ("243 I", "243I"),
        ("243Z-I", "243ZI"),
    ],
)
def test_normalize_article_identifier(
    value: str,
    expected: str,
) -> None:
    assert normalize_article_identifier(value) == expected
