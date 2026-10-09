from hashlib import sha256
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
)


CONSTITUTION_ENGLISH_URL = (
    "https://www.legislative.gov.in/static/uploads/"
    "2025/07/c9fe9c9b6840524844316f74bb1c556c.pdf"
)

CONSTITUTION_BILINGUAL_URL = (
    "https://www.legislative.gov.in/static/uploads/"
    "2025/08/575648bd8ecb7654db902b93115d35e4.pdf"
)


ENGLISH_OUTPUT_FILE = (
    OUTPUT_DIR
    / "constitution_2026_english.pdf"
)

BILINGUAL_OUTPUT_FILE = (
    OUTPUT_DIR
    / "constitution_2026_hindi_english.pdf"
)


def calculate_sha256(
    file_path: Path,
) -> str:
    hasher = sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()


def download_pdf(
    url: str,
    output_file: Path,
    label: str,
) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Downloading {label}...")

    with httpx.Client(
        follow_redirects=True,
        timeout=120.0,
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    content = response.content

    # Defensive check so an HTML error page is never
    # silently stored as a legal PDF.
    if not content.startswith(b"%PDF"):
        raise RuntimeError(
            f"{label} download did not return a valid PDF."
        )

    output_file.write_bytes(content)

    file_hash = calculate_sha256(
        output_file
    )

    print(f"{label} downloaded successfully.")
    print(f"File: {output_file}")
    print(
        f"Size: "
        f"{output_file.stat().st_size:,} bytes"
    )
    print(f"SHA-256: {file_hash}")
    print()


def main() -> None:
    download_pdf(
        url=CONSTITUTION_ENGLISH_URL,
        output_file=ENGLISH_OUTPUT_FILE,
        label=(
            "Constitution of India "
            "English PDF"
        ),
    )

    download_pdf(
        url=CONSTITUTION_BILINGUAL_URL,
        output_file=BILINGUAL_OUTPUT_FILE,
        label=(
            "Constitution of India "
            "Hindi-English PDF"
        ),
    )


if __name__ == "__main__":
    main()