import asyncio

from app.services.embeddings import (
    get_embedding_provider,
)


async def test_embedding():

    provider = get_embedding_provider()

    text = (
        "The Bharatiya Nyaya Sanhita, 2023 "
        "contains provisions relating to offences."
    )

    print("Generating test embedding...")

    embedding = await provider.embed_text(text)

    print("Embedding generated successfully.")

    print(
        f"Embedding dimensions: {len(embedding)}"
    )

    print(
        f"First 5 values: {embedding[:5]}"
    )


if __name__ == "__main__":
    asyncio.run(test_embedding())