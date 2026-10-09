from app.services.query_analyzer import (
    get_query_analyzer,
)


def main() -> None:

    analyzer = get_query_analyzer()

    test_queries = [
        "What is the punishment for theft?",
        "My landlord is refusing to return my deposit.",
        "Someone hacked my Instagram account.",
        "Where do I report a stolen bike?",
        "What documents should I keep as evidence?",
        "Someone is attacking me right now.",
        "How do I file a complaint against a company in Assam?",
    ]

    print("=" * 80)
    print("NYAYAAI — QUERY ANALYZER TEST")
    print("=" * 80)

    for index, query in enumerate(
        test_queries,
        start=1,
    ):

        result = analyzer.analyze(
            query
        )

        print("\n" + "-" * 80)
        print(f"TEST {index}")
        print(f"Query: {query}")

        print(
            f"Intent: "
            f"{result.intent.value}"
        )

        print(
            f"Domain: "
            f"{result.domain.value}"
        )

        print(
            f"Jurisdiction: "
            f"{result.jurisdiction}"
        )

        print(
            f"Urgency: "
            f"{result.urgency.value}"
        )

        print(
            f"Keywords: "
            f"{result.keywords}"
        )

        print(
            f"Rewritten queries: "
            f"{result.rewritten_queries}"
        )

        print(
            f"Requires follow-up: "
            f"{result.requires_follow_up}"
        )

        print(
            f"Missing information: "
            f"{result.missing_information}"
        )


if __name__ == "__main__":
    main()