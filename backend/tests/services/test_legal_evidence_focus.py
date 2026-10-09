from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.legal_chunk import LegalChunk
from app.schemas.legal_query_plan import LegalQuestionAspect
from app.services.legal_evidence_focus import focus_legal_chunks


def make_chunk(
    *,
    chunk_id: int,
    section_id: int,
    subsection_id: int | None,
    content: str,
) -> LegalChunk:
    return LegalChunk(
        id=chunk_id,
        document_id=2,
        act_id=1,
        version_id=1,
        section_id=section_id,
        subsection_id=subsection_id,
        chunk_index=0,
        content=content,
    )


def database_returning(
    chunks: list[LegalChunk],
) -> AsyncMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = chunks

    db = AsyncMock()
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_scenario_focuses_and_completes_definition_and_punishment():
    hurt = make_chunk(
        chunk_id=1,
        section_id=122,
        subsection_id=1221,
        content="Hurt on grave and sudden provocation.",
    )
    snatching_definition = make_chunk(
        chunk_id=2,
        section_id=304,
        subsection_id=3041,
        content=(
            "Theft is snatching if the offender suddenly or forcibly "
            "grabs movable property from any person."
        ),
    )
    ordinary_theft = make_chunk(
        chunk_id=3,
        section_id=303,
        subsection_id=3032,
        content="Whoever commits theft shall be punished.",
    )
    snatching_punishment = make_chunk(
        chunk_id=4,
        section_id=304,
        subsection_id=3042,
        content=(
            "Whoever commits snatching shall be punished with "
            "imprisonment and fine."
        ),
    )

    db = database_returning(
        [snatching_definition, snatching_punishment]
    )

    result = await focus_legal_chunks(
        db=db,
        user_query=(
            "A rider suddenly grabbed a phone from someone's hand. "
            "Which offence describes this and what is the punishment?"
        ),
        retrieval_queries=[
            "sudden phone theft",
            "offence for grabbing phone from hand",
        ],
        chunks=[hurt, ordinary_theft, snatching_definition],
        requested_aspects=[
            LegalQuestionAspect.DEFINITION,
            LegalQuestionAspect.PUNISHMENT,
        ],
    )

    assert [chunk.id for chunk in result] == [2, 4]
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_constitution_quote_focuses_exact_matching_article():
    article_21 = make_chunk(
        chunk_id=21,
        section_id=21,
        subsection_id=None,
        content=(
            "Article 21. No person shall be deprived of life or "
            "personal liberty except according to procedure "
            "established by law."
        ),
    )
    article_22 = make_chunk(
        chunk_id=22,
        section_id=22,
        subsection_id=None,
        content="Article 22. Protection against arrest and detention.",
    )
    article_359 = make_chunk(
        chunk_id=359,
        section_id=359,
        subsection_id=None,
        content="Article 359. A Proclamation of Emergency is in force.",
    )

    db = database_returning([article_21])

    result = await focus_legal_chunks(
        db=db,
        user_query=(
            "Which constitutional protection says a person cannot be "
            "deprived of life or personal liberty except according to "
            "procedure established by law?"
        ),
        retrieval_queries=[],
        chunks=[article_21, article_22, article_359],
        requested_aspects=[LegalQuestionAspect.RIGHT],
    )

    assert [chunk.id for chunk in result] == [21]


@pytest.mark.asyncio
async def test_definition_and_base_punishment_exclude_special_offences():
    definition = make_chunk(
        chunk_id=1131,
        section_id=113,
        subsection_id=1,
        content=(
            "A person who performs the listed acts with the required "
            "intent commits a terrorist act."
        ),
    )
    base_punishment = make_chunk(
        chunk_id=1132,
        section_id=113,
        subsection_id=2,
        content=(
            "Whoever commits a terrorist act shall be punished with "
            "the stated imprisonment and fine."
        ),
    )
    membership = make_chunk(
        chunk_id=1135,
        section_id=113,
        subsection_id=5,
        content=(
            "A member of an organisation involved in a terrorist act "
            "shall be punished."
        ),
    )

    db = database_returning(
        [definition, base_punishment, membership]
    )

    result = await focus_legal_chunks(
        db=db,
        user_query=(
            "How does the BNS define a terrorist act and what "
            "punishment does the provision state?"
        ),
        retrieval_queries=[],
        chunks=[membership, base_punishment],
        requested_aspects=[
            LegalQuestionAspect.DEFINITION,
            LegalQuestionAspect.PUNISHMENT,
        ],
    )

    assert [chunk.id for chunk in result] == [1131, 1132]


@pytest.mark.asyncio
async def test_comparison_query_preserves_multiple_sections():
    theft = make_chunk(
        chunk_id=303,
        section_id=303,
        subsection_id=1,
        content="Definition of theft.",
    )
    snatching = make_chunk(
        chunk_id=304,
        section_id=304,
        subsection_id=1,
        content="Definition of snatching.",
    )
    db = AsyncMock()

    result = await focus_legal_chunks(
        db=db,
        user_query="Compare theft and snatching under the BNS.",
        retrieval_queries=[],
        chunks=[theft, snatching],
        requested_aspects=[LegalQuestionAspect.COMPARISON],
    )

    assert result == [theft, snatching]
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_punishment_focus_prefers_relevant_subsection_over_generic_one():
    generic_murder = make_chunk(
        chunk_id=1031,
        section_id=103,
        subsection_id=1,
        content=(
            "Whoever commits murder shall be punished with death or "
            "imprisonment for life and shall also be liable to fine."
        ),
    )
    group_murder = make_chunk(
        chunk_id=1032,
        section_id=103,
        subsection_id=2,
        content=(
            "When a group of five or more persons acting in concert "
            "commits murder on the stated grounds, each member shall "
            "be punished with death or imprisonment for life and fine."
        ),
    )
    db = database_returning([generic_murder, group_murder])

    result = await focus_legal_chunks(
        db=db,
        user_query=(
            "What is the provision for mob lynching under the BNS, "
            "and what is the punishment?"
        ),
        retrieval_queries=[
            "group of five or more persons acting in concert commits murder"
        ],
        chunks=[group_murder],
        requested_aspects=[LegalQuestionAspect.PUNISHMENT],
    )

    assert [chunk.id for chunk in result] == [1032]
    statement = db.execute.await_args.args[0]
    compiled = str(
        statement.compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    assert "legal_chunks.section_id = 103" in compiled


@pytest.mark.asyncio
async def test_generic_legal_scaffolding_preserves_candidates_instead_of_section_one():
    commencement = make_chunk(
        chunk_id=1,
        section_id=1,
        subsection_id=11,
        content=(
            "This Act may be called the Bharatiya Nyaya Sanhita and "
            "this provision extends to India."
        ),
    )
    group_murder = make_chunk(
        chunk_id=1032,
        section_id=103,
        subsection_id=1032,
        content=(
            "When a group of five or more persons acting in concert "
            "commits murder on specified grounds, each member shall "
            "be punished with death or imprisonment for life and fine."
        ),
    )
    db = AsyncMock()

    result = await focus_legal_chunks(
        db=db,
        user_query=(
            "What provision covers lynching by a mob under the BNS, "
            "and what punishment can apply?"
        ),
        retrieval_queries=[
            "Bharatiya Nyaya Sanhita mob lynching provision",
            "BNS punishment for mob lynching",
            "Bharatiya Nyaya Sanhita section on mob violence",
        ],
        chunks=[commencement, group_murder],
        requested_aspects=[LegalQuestionAspect.PUNISHMENT],
    )

    assert result == [commencement, group_murder]
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_punishment_question_preserves_candidates_without_penalty_evidence():
    commencement = make_chunk(
        chunk_id=1,
        section_id=1,
        subsection_id=11,
        content=(
            "This Act may be called the Bharatiya Nyaya Sanhita and "
            "this provision extends to India."
        ),
    )
    definitions_only = make_chunk(
        chunk_id=2,
        section_id=9,
        subsection_id=91,
        content="This provision defines a general legal expression.",
    )
    db = AsyncMock()

    result = await focus_legal_chunks(
        db=db,
        user_query=(
            "What is the provision under the BNS and its punishment?"
        ),
        retrieval_queries=["BNS provision and punishment"],
        chunks=[commencement, definitions_only],
        requested_aspects=[LegalQuestionAspect.PUNISHMENT],
    )

    assert result == [commencement, definitions_only]
    db.execute.assert_not_awaited()
