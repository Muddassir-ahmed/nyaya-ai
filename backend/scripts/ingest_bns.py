from pathlib import Path
from hashlib import sha256

import httpx


BNS_URL = (
    "https://www.mha.gov.in/sites/default/files/"
    "250883_english_01042024.pdf"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "legal" / "central"

OUTPUT_FILE = OUTPUT_DIR / "bns_2023_gazette.pdf"


def calculate_sha256(file_path: Path) -> str:
    hasher = sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()


def download_bns_pdf() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Downloading BNS Gazette PDF...")

    with httpx.Client(
        follow_redirects=True,
        timeout=60.0,
    ) as client:

        response = client.get(BNS_URL)
        response.raise_for_status()

        OUTPUT_FILE.write_bytes(response.content)

    file_hash = calculate_sha256(OUTPUT_FILE)

    print("BNS PDF downloaded successfully.")
    print(f"File: {OUTPUT_FILE}")
    print(f"Size: {OUTPUT_FILE.stat().st_size:,} bytes")
    print(f"SHA-256: {file_hash}")


if __name__ == "__main__":
    download_bns_pdf()