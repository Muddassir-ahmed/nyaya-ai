from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalExample:
    query: str
    expected_section_numbers: tuple[str, ...]


RETRIEVAL_DATASET = [
    RetrievalExample(
        query="What is the punishment for theft?",
        expected_section_numbers=("303",),
    ),
    RetrievalExample(
        query="What is theft under the Bharatiya Nyaya Sanhita?",
        expected_section_numbers=("303",),
    ),
    RetrievalExample(
        query="What is criminal breach of trust?",
        expected_section_numbers=("316",),
    ),
    RetrievalExample(
        query="What is cheating under the BNS?",
        expected_section_numbers=("318",),
    ),
    RetrievalExample(
        query="What is criminal trespass and house-trespass?",
        expected_section_numbers=("329",),
    ),
]