from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PDF_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette.pdf"
)


def debug_page(page_number: int) -> None:
    reader = PdfReader(PDF_FILE)

    page = reader.pages[page_number - 1]

    print(
        f"\n===== PDF PAGE {page_number} =====\n"
    )

    def visitor_text(
        text,
        cm,
        tm,
        font_dict,
        font_size,
    ):
        cleaned = text.strip()

        if not cleaned:
            return

        x = tm[4]
        y = tm[5]

        print(
            f"x={x:8.2f} "
            f"y={y:8.2f} "
            f"size={font_size:5.1f} "
            f"| {cleaned}"
        )

    page.extract_text(
        visitor_text=visitor_text
    )


if __name__ == "__main__":
    debug_page(80)
    debug_page(81)