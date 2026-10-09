import asyncio

from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
)
from app.services.llm_factory import (
    get_llm_provider,
)


async def main():

    provider = get_llm_provider()

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content=(
                    "Explain what the Bharatiya "
                    "Nyaya Sanhita is in one sentence."
                ),
            )
        ],
        temperature=0.1,
        max_tokens=100,
    )

    response = await provider.generate(
        request
    )

    print("\nProvider:")
    print(response.provider)

    print("\nModel:")
    print(response.model)

    print("\nResponse:")
    print(response.content)

    print("\nPrompt tokens:")
    print(response.prompt_tokens)

    print("\nCompletion tokens:")
    print(response.completion_tokens)


if __name__ == "__main__":
    asyncio.run(main())