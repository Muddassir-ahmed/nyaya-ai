from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "constitution_2026_english.pdf"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "constitution_2026_english.txt"
)


def extract_constitution_text() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Constitution PDF not found: "
            f"{INPUT_FILE}"
        )

    print(
        "Reading Constitution of India "
        "English PDF..."
    )

    reader = PdfReader(INPUT_FILE)

    total_pages = len(reader.pages)

    print(
        f"Total pages: {total_pages}"
    )

    extracted_pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        print(
            "Extracting page "
            f"{page_number}/{total_pages}..."
        )

        text = page.extract_text() or ""

        extracted_pages.append(
            f"\n===== PAGE {page_number} =====\n\n"
            f"{text.strip()}\n"
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        "\n".join(extracted_pages),
        encoding="utf-8",
    )

    print(
        "\nConstitution text extraction "
        "completed."
    )
    print(
        f"Output file: {OUTPUT_FILE}"
    )
    print(
        f"Characters: "
        f"{OUTPUT_FILE.stat().st_size:,}"
    )


if __name__ == "__main__":
    extract_constitution_text()