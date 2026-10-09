from pathlib import Path
from collections import defaultdict

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette.pdf"
)

# Preserve the original, unfiltered extraction
# for debugging/audit purposes.
RAW_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette.txt"
)

# Coordinate-filtered legal body text.
CLEAN_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_2023_gazette_clean.txt"
)


# ---------------------------------------------------------
# PDF LAYOUT BOUNDS
# ---------------------------------------------------------
#
# Inspection of the official BNS Gazette shows:
#
# Main statutory body:
#     x ~= 245 -> 565
#
# Left marginal headings:
#     x ~= 120
#
# Right marginal headings:
#     x ~= 1015
#
# Gazette running header / rule:
#     y ~= 146 -> 157
#
# Main body begins:
#     y ~= 190
#
# We deliberately use wider bounds than the observed
# statutory column so legitimate indentation and centered
# headings are retained.
BODY_X_MIN = 200.0
BODY_X_MAX = 900.0
BODY_Y_MIN = 170.0

# Text fragments on the same printed line normally share
# the same y-coordinate. Rounding protects against tiny
# floating-point differences.
Y_ROUND_DIGITS = 2


def should_keep_fragment(
    x: float,
    y: float,
) -> bool:
    """
    Return True only for text fragments located inside
    the main legal-text region of a Gazette page.

    This removes:

    - left marginal headings;
    - right marginal headings;
    - running Gazette headers;
    - horizontal underscore rules;
    - pypdf duplicate x=0/y=0 page-text callbacks.
    """

    if x == 0.0 and y == 0.0:
        return False

    if x < BODY_X_MIN:
        return False

    if x > BODY_X_MAX:
        return False

    if y < BODY_Y_MIN:
        return False

    return True


def rebuild_page_lines(
    fragments: list[
        tuple[float, float, int, str]
    ],
) -> str:
    """
    Reconstruct normal text lines from coordinate-aware
    pypdf fragments.

    fragments:
        (
            y_coordinate,
            x_coordinate,
            original_order,
            text,
        )

    Fragments sharing the same y-coordinate are joined
    left-to-right.
    """

    lines_by_y = defaultdict(list)

    for (
        y,
        x,
        order,
        text,
    ) in fragments:
        y_key = round(
            y,
            Y_ROUND_DIGITS,
        )

        lines_by_y[y_key].append(
            (
                x,
                order,
                text,
            )
        )

    rebuilt_lines = []

    for y in sorted(lines_by_y):
        pieces = sorted(
            lines_by_y[y],
            key=lambda item: (
                item[0],
                item[1],
            ),
        )

        line = "".join(
            piece[2]
            for piece in pieces
        ).strip()

        if line:
            rebuilt_lines.append(
                line
            )

    return "\n".join(
        rebuilt_lines
    )


def extract_page(
    page,
) -> tuple[str, str]:
    """
    Extract both:

    1. the original pypdf text; and
    2. coordinate-filtered statutory body text.
    """

    fragments = []

    fragment_order = 0

    def visitor_text(
        text,
        cm,
        tm,
        font_dict,
        font_size,
    ):
        nonlocal fragment_order

        # Keep spaces inside a fragment because pypdf may
        # split things such as:
        #
        #   "304." + "(" + "1" + ") Theft..."
        #
        # Newline characters are removed because line
        # reconstruction is based on PDF coordinates.
        piece = (
            text
            .replace("\r", "")
            .replace("\n", "")
        )

        if not piece.strip():
            return

        x = float(tm[4])
        y = float(tm[5])

        current_order = (
            fragment_order
        )

        fragment_order += 1

        if not should_keep_fragment(
            x=x,
            y=y,
        ):
            return

        fragments.append(
            (
                y,
                x,
                current_order,
                piece,
            )
        )

    raw_text = (
        page.extract_text(
            visitor_text=visitor_text
        )
        or ""
    )

    clean_text = rebuild_page_lines(
        fragments
    )

    return (
        raw_text.strip(),
        clean_text.strip(),
    )


def extract_bns_text() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"BNS PDF not found: "
            f"{INPUT_FILE}"
        )

    print(
        "Reading BNS Gazette PDF..."
    )

    reader = PdfReader(
        INPUT_FILE
    )

    print(
        f"Total pages: "
        f"{len(reader.pages)}"
    )

    raw_pages = []
    clean_pages = []

    for (
        page_number,
        page,
    ) in enumerate(
        reader.pages,
        start=1,
    ):
        print(
            f"Extracting page "
            f"{page_number}/"
            f"{len(reader.pages)}..."
        )

        (
            raw_text,
            clean_text,
        ) = extract_page(
            page
        )

        raw_pages.append(
            f"\n===== PAGE "
            f"{page_number} =====\n\n"
            f"{raw_text}\n"
        )

        clean_pages.append(
            f"\n===== PAGE "
            f"{page_number} =====\n\n"
            f"{clean_text}\n"
        )

    RAW_OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_OUTPUT_FILE.write_text(
        "\n".join(
            raw_pages
        ),
        encoding="utf-8",
    )

    CLEAN_OUTPUT_FILE.write_text(
        "\n".join(
            clean_pages
        ),
        encoding="utf-8",
    )

    print(
        "\nBNS text extraction completed."
    )

    print(
        f"Raw output: "
        f"{RAW_OUTPUT_FILE}"
    )

    print(
        f"Clean output: "
        f"{CLEAN_OUTPUT_FILE}"
    )

    print(
        f"Raw characters: "
        f"{RAW_OUTPUT_FILE.stat().st_size:,}"
    )

    print(
        f"Clean characters: "
        f"{CLEAN_OUTPUT_FILE.stat().st_size:,}"
    )


if __name__ == "__main__":
    extract_bns_text()