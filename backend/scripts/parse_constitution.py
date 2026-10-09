from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
)

INPUT_FILE = (
    DATA_DIR
    / "constitution_2026_english.txt"
)

SOURCE_PDF = (
    DATA_DIR
    / "constitution_2026_english.pdf"
)

OUTPUT_FILE = (
    DATA_DIR
    / "constitution_parsed.json"
)


EXPECTED_PDF_SHA256 = (
    "4C8E93689EC245E26DB08E22B5FF3AD"
    "645C98736F0E5B7C8B6638ACD7861F85B"
)


PAGE_PATTERN = re.compile(
    r"^===== PAGE \d+ =====$"
)


ARTICLE_ID_PATTERN = (
    r"\d{1,3}"
    r"(?:"
    r"[A-Z]+(?:-[A-Z])?"
    r"|-[A-Z]"
    r")?"
)


ARTICLE_TOKEN_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9])"
    rf"(?:\d+\[)*"
    rf"\[?\s*"
    rf"(?P<number>{ARTICLE_ID_PATTERN})"
    rf"\s*\."
)


PART_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z])"
    r"(?:\d+\[)*"
    r"\[?\s*"
    r"PART\s*"
    r"(?P<number>[IVXLC]+[A-Z]?)"
    r"\b"
)


CHAPTER_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z])"
    r"CHAPTER\s*"
    r"(?P<number>[IVXLC]+)"
    r"\b"
)


SCHEDULE_NAMES = [
    "FIRST",
    "SECOND",
    "THIRD",
    "FOURTH",
    "FIFTH",
    "SIXTH",
    "SEVENTH",
    "EIGHTH",
    "NINTH",
    "TENTH",
    "ELEVENTH",
    "TWELFTH",
]


REQUIRED_ARTICLES = {
    "1",
    "14",
    "19",
    "21",
    "21A",
    "32",
    "51A",
    "226",
    "238",
    "239",
    "239AA",
    "243-I",
    "243-O",
    "243Z-I",
    "243Z-O",
    "368",
    "369",
    "370",
    "371",
    "371-I",
    "394A",
    "395",
}


SAMPLE_ARTICLES = [
    "1",
    "14",
    "19",
    "21",
    "21A",
    "32",
    "51A",
    "226",
    "239AA",
    "243-I",
    "243Z-I",
    "368",
    "370",
    "371-I",
    "394A",
    "395",
]


def calculate_sha256(
    file_path: Path,
) -> str:
    hasher = sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(
            1024 * 1024
        ):
            hasher.update(chunk)

    return hasher.hexdigest().upper()


def clean_line(
    raw_line: str,
) -> str:
    return " ".join(
        raw_line.strip().split()
    )


def is_page_marker(
    line: str,
) -> bool:
    return bool(
        PAGE_PATTERN.fullmatch(line)
    )


def letters_only(
    value: str,
) -> str:
    return "".join(
        character.upper()
        for character in value
        if character.isalpha()
    )


def is_upper_heading_text(
    line: str,
) -> bool:
    letters = [
        character
        for character in line
        if character.isalpha()
    ]

    if not letters:
        return False

    return (
        line.upper() == line
        and len(line) <= 140
        and not is_page_marker(line)
    )


def locate_first_exact(
    lines: list[str],
    target: str,
    *,
    start: int = 0,
    end: int | None = None,
) -> int:
    stop = (
        len(lines)
        if end is None
        else end
    )

    for index in range(
        start,
        stop,
    ):
        if lines[index] == target:
            return index

    raise RuntimeError(
        f"Could not locate exact line: "
        f"{target}"
    )


def locate_preamble(
    lines: list[str],
) -> tuple[int, int]:
    people_index = None

    for index, line in enumerate(lines):
        if (
            "WE, THE PEOPLE OF INDIA"
            in line
        ):
            people_index = index
            break

    if people_index is None:
        raise RuntimeError(
            "Could not locate "
            "'WE, THE PEOPLE OF INDIA'."
        )

    preamble_heading = None

    for index in range(
        people_index,
        -1,
        -1,
    ):
        if lines[index] == "PREAMBLE":
            preamble_heading = index
            break

    if preamble_heading is None:
        raise RuntimeError(
            "Could not locate the real "
            "PREAMBLE heading."
        )

    preamble_end = None

    for index in range(
        people_index,
        min(
            len(lines),
            people_index + 80,
        ),
    ):
        if (
            "THIS CONSTITUTION."
            in lines[index]
        ):
            preamble_end = index
            break

    if preamble_end is None:
        raise RuntimeError(
            "Could not locate the end "
            "of the Preamble."
        )

    return (
        preamble_heading,
        preamble_end,
    )


def locate_actual_part_one(
    lines: list[str],
    preamble_end: int,
) -> int:
    for index in range(
        preamble_end + 1,
        len(lines),
    ):
        if lines[index] == "PART I":
            return index

    raise RuntimeError(
        "Could not locate actual "
        "PART I after the Preamble."
    )


def normalize_article_number(
    value: str,
) -> str:
    return (
        value
        .replace(" ", "")
        .upper()
    )


def article_numeric_base(
    article_number: str,
) -> int:
    match = re.match(
        r"^(\d+)",
        article_number,
    )

    if not match:
        raise ValueError(
            "Invalid Article number: "
            f"{article_number}"
        )

    return int(
        match.group(1)
    )


def find_part_events(
    line: str,
) -> list[tuple[int, str]]:
    events = []

    for match in (
        PART_TOKEN_PATTERN.finditer(line)
    ):
        events.append(
            (
                match.start(),
                match
                .group("number")
                .upper(),
            )
        )

    return events


def find_article_events(
    line: str,
) -> list[tuple[int, str]]:
    events = []

    for match in (
        ARTICLE_TOKEN_PATTERN
        .finditer(line)
    ):
        number = (
            normalize_article_number(
                match.group("number")
            )
        )

        events.append(
            (
                match.start(),
                number,
            )
        )

    return events


def extract_part_titles(
    lines: list[str],
    start_index: int,
    end_index: int,
) -> dict[str, str]:
    titles: dict[str, str] = {}

    for index in range(
        start_index,
        end_index,
    ):
        line = lines[index]

        part_matches = list(
            PART_TOKEN_PATTERN.finditer(
                line
            )
        )

        if not part_matches:
            continue

        for part_match in part_matches:
            part_number = (
                part_match
                .group("number")
                .upper()
            )

            if part_number in titles:
                continue

            pieces: list[str] = []

            suffix = (
                line[
                    part_match.end():
                ]
                .strip(
                    " .—–⎯-[]"
                )
            )

            if (
                suffix
                and is_upper_heading_text(
                    suffix
                )
            ):
                pieces.append(suffix)

            for look_ahead in range(
                index + 1,
                min(
                    end_index,
                    index + 5,
                ),
            ):
                candidate = (
                    lines[look_ahead]
                )

                if candidate == "ARTICLES":
                    continue

                if (
                    not candidate
                    or is_page_marker(
                        candidate
                    )
                ):
                    continue

                if (
                    PART_TOKEN_PATTERN
                    .search(candidate)
                    or
                    CHAPTER_TOKEN_PATTERN
                    .search(candidate)
                    or
                    ARTICLE_TOKEN_PATTERN
                    .search(candidate)
                ):
                    break

                if is_upper_heading_text(
                    candidate
                ):
                    pieces.append(
                        candidate.strip(
                            " .—–⎯-[]"
                        )
                    )
                    continue

                break

            title = " ".join(
                piece
                for piece in pieces
                if piece
            ).strip()

            if title == "OMITTED":
                title = ""

            titles[
                part_number
            ] = title

    return titles




def parse_toc_article_index(
    lines: list[str],
    contents_index: int,
    toc_schedules_index: int,
) -> tuple[
    list[dict[str, Any]],
    dict[str, str],
]:
    """
    Build the authoritative Article sequence
    from the official Constitution Contents.

    The Contents is used as the canonical index
    for:

    - Article numbers
    - Part association
    - Part titles
    - TOC source locations
    - omitted-provision status

    The exact column position of each Article
    heading is stored so that multiple Articles
    appearing on the same extracted text line
    do not contaminate each other's metadata.
    """

    part_titles = extract_part_titles(
        lines,
        contents_index,
        toc_schedules_index,
    )

    articles: list[
        dict[str, Any]
    ] = []

    seen: set[str] = set()

    current_part: str | None = None

    last_base = 0

    # -------------------------------------------------
    # PASS 1:
    # Build authoritative Article sequence from TOC
    # -------------------------------------------------

    for line_index in range(
        contents_index,
        toc_schedules_index,
    ):
        line = lines[line_index]

        if (
            not line
            or is_page_marker(line)
        ):
            continue

        events: list[
            tuple[int, str, str]
        ] = []

        # Detect Part headings.
        for (
            position,
            part_number,
        ) in find_part_events(line):
            events.append(
                (
                    position,
                    "part",
                    part_number,
                )
            )

        # Detect Article headings.
        for (
            position,
            article_number,
        ) in find_article_events(line):
            events.append(
                (
                    position,
                    "article",
                    article_number,
                )
            )

        # Important when a Part heading and
        # Article heading occur on one PDF
        # extraction line.
        events.sort(
            key=lambda item: item[0]
        )

        for (
            event_position,
            event_type,
            value,
        ) in events:

            # -----------------------------
            # Part event
            # -----------------------------

            if event_type == "part":
                current_part = value
                continue

            # -----------------------------
            # Article event
            # -----------------------------

            article_number = value

            # Ignore duplicate Article IDs
            # produced by extraction noise.
            if article_number in seen:
                continue

            base = article_numeric_base(
                article_number
            )

            # References inside Article titles
            # normally point backwards.
            #
            # Example:
            #
            # Article 357's title may mention
            # Article 356.
            #
            # That reference must not become
            # another Article heading.
            if base < last_base:
                continue

            # Constitution body ends at
            # Article 395.
            if base > 395:
                continue

            seen.add(
                article_number
            )

            last_base = base

            articles.append(
                {
                    "article_number":
                        article_number,

                    "part":
                        current_part,

                    "part_title":
                        part_titles.get(
                            current_part
                            or "",
                            "",
                        ),

                    # Human-readable,
                    # 1-based source line.
                    "toc_source_line":
                        line_index + 1,

                    # Exact position inside
                    # that extracted line.
                    #
                    # Required because pypdf
                    # can place multiple Article
                    # entries on one line.
                    "toc_column":
                        event_position,
                }
            )

    # -------------------------------------------------
    # Basic TOC integrity checks
    # -------------------------------------------------

    if not articles:
        raise RuntimeError(
            "No Article index could "
            "be parsed from Contents."
        )

    if (
        articles[0][
            "article_number"
        ]
        != "1"
    ):
        raise RuntimeError(
            "Contents parser did not "
            "start with Article 1. "
            "Found: "
            f"{articles[0]['article_number']}"
        )

    if (
        articles[-1][
            "article_number"
        ]
        != "395"
    ):
        raise RuntimeError(
            "Contents parser did not "
            "end with Article 395. "
            "Found: "
            f"{articles[-1]['article_number']}"
        )

    # -------------------------------------------------
    # PASS 2:
    # Extract each Article's EXACT TOC entry
    # -------------------------------------------------
    #
    # Previously we took everything from the
    # current Article's source line until the
    # next Article's source line.
    #
    # That caused false omitted classifications:
    #
    # Article 2    -> accidentally inherited
    #                 "2A ... Omitted"
    #
    # Article 144  -> accidentally inherited
    #                 "144A ... Omitted"
    #
    # etc.
    #
    # We now use BOTH:
    #
    #   toc_source_line
    #   toc_column
    #
    # so every Article gets only its own TOC
    # text.

    for index, article in enumerate(
        articles
    ):
        start_line = (
            article[
                "toc_source_line"
            ]
            - 1
        )

        start_column = article[
            "toc_column"
        ]

        # -----------------------------------------
        # Determine exact end boundary
        # -----------------------------------------

        if (
            index + 1
            < len(articles)
        ):
            next_article = (
                articles[index + 1]
            )

            end_line = (
                next_article[
                    "toc_source_line"
                ]
                - 1
            )

            end_column = (
                next_article[
                    "toc_column"
                ]
            )

        else:
            # Article 395 ends where the
            # SCHEDULES TOC section begins.
            end_line = (
                toc_schedules_index
            )

            end_column = 0

        # -----------------------------------------
        # Same-line Article entries
        # -----------------------------------------
        #
        # Example:
        #
        # 31. ...
        # [31A. ...]
        #
        # pypdf may combine them into one line.
        #
        # We slice by exact character columns.

        if start_line == end_line:
            toc_raw_text = (
                lines[start_line][
                    start_column:
                    end_column
                ]
                .strip()
            )

        else:
            pieces: list[str] = []

            # First line:
            # begin exactly at this Article.
            first_piece = (
                lines[start_line][
                    start_column:
                ]
                .strip()
            )

            if first_piece:
                pieces.append(
                    first_piece
                )

            # Middle lines belong entirely
            # to this TOC entry.
            for line_number in range(
                start_line + 1,
                end_line,
            ):
                candidate = (
                    lines[line_number]
                    .strip()
                )

                if (
                    not candidate
                    or is_page_marker(
                        candidate
                    )
                ):
                    continue

                pieces.append(
                    candidate
                )

            # Final line:
            #
            # Include only text BEFORE the
            # next Article starts.
            if (
                end_line
                < toc_schedules_index
                and end_column > 0
            ):
                final_piece = (
                    lines[end_line][
                        :end_column
                    ]
                    .strip()
                )

                if (
                    final_piece
                    and not is_page_marker(
                        final_piece
                    )
                ):
                    pieces.append(
                        final_piece
                    )

            toc_raw_text = " ".join(
                pieces
            ).strip()

        # Store exact source text used for
        # metadata/provenance.
                # -----------------------------------------
        # Stop at a following structural heading
        # -----------------------------------------
        #
        # Example:
        #
        # 237. Application of the provisions ...
        # [PART VII.—Omitted.]
        # 238. [Omitted.]
        #
        # PART VII belongs to the document
        # structure, NOT to Article 237.
        #
        # Without this clipping Article 237 would
        # incorrectly inherit the word "Omitted".

        article_match = (
            article_heading_regex(
                article[
                    "article_number"
                ]
            )
            .search(
                toc_raw_text
            )
        )

        structural_search_start = (
            article_match.end()
            if article_match
            else 0
        )

        structural_positions: list[int] = []

        part_match = (
            PART_TOKEN_PATTERN.search(
                toc_raw_text,
                structural_search_start,
            )
        )

        if part_match:
            structural_positions.append(
                part_match.start()
            )

        chapter_match = (
            CHAPTER_TOKEN_PATTERN.search(
                toc_raw_text,
                structural_search_start,
            )
        )

        if chapter_match:
            structural_positions.append(
                chapter_match.start()
            )

        if structural_positions:
            structural_boundary = min(
                structural_positions
            )

            toc_raw_text = (
                toc_raw_text[
                    :structural_boundary
                ]
                .strip()
            )

        # -----------------------------------------
        # Store exact Article-specific TOC text
        # -----------------------------------------

        article[
            "toc_raw_text"
        ] = toc_raw_text

        # -----------------------------------------
        # Omitted status
        # -----------------------------------------
        #
        # At this stage toc_raw_text contains
        # ONLY this Article's TOC entry.
        #
        # Therefore "Omitted" can safely be
        # treated as Article-level status.

        article[
            "is_omitted"
        ] = bool(
            re.search(
                r"\bOMITTED\b",
                toc_raw_text,
                flags=re.IGNORECASE,
            )
        )

    return (
        articles,
        part_titles,
    )


def article_heading_regex(
    article_number: str,
) -> re.Pattern[str]:
    """
    Match an Article heading while tolerating
    pypdf formatting differences.

    Examples:

        TOC:  243-I
        body: 243I

        TOC:  243Z-I
        body: 243 ZI

        TOC:  243Z-O
        body: 243ZO
    """

    compact = (
        article_number
        .replace("-", "")
        .replace(" ", "")
        .upper()
    )

    match = re.fullmatch(
        r"(\d+)([A-Z]*)",
        compact,
    )

    if not match:
        raise ValueError(
            "Invalid Article number: "
            f"{article_number}"
        )

    base = match.group(1)
    suffix = match.group(2)

    suffix_pattern = "".join(
        rf"\s*-?\s*{re.escape(letter)}"
        for letter in suffix
    )

    return re.compile(
        rf"(?<![A-Za-z0-9])"
        rf"(?:\d+\[)*"
        rf"\[?\s*"
        rf"{re.escape(base)}"
        rf"{suffix_pattern}"
        rf"\s*\."
    )


def prefix_allows_heading(
    prefix: str,
) -> bool:
    """
    pypdf sometimes merges a structural
    heading and Article heading:

        THE PANCHAYATS243A. Gram Sabha.

    Such an uppercase prefix is safe.

    A normal sentence prefix such as:

        under article 370.

    is not.
    """

    if not prefix:
        return True

    letters = "".join(
        character
        for character in prefix
        if character.isalpha()
    )

    if not letters:
        return True

    return (
        letters.upper()
        == letters
    )


def find_expected_article_position(
    lines: list[str],
    article_number: str,
    *,
    start_line: int,
    start_column: int,
    end_line: int,
) -> tuple[
    int,
    int,
    int,
] | None:

    pattern = (
        article_heading_regex(
            article_number
        )
    )

    for line_index in range(
        start_line,
        end_line,
    ):
        line = lines[line_index]

        search_from = (
            start_column
            if line_index == start_line
            else 0
        )

        if search_from >= len(line):
            continue

        for match in pattern.finditer(
            line,
            search_from,
        ):
            prefix = line[
                search_from:
                match.start()
            ]

            if (
                search_from > 0
                or prefix_allows_heading(
                    prefix
                )
            ):
                return (
                    line_index,
                    match.start(),
                    match.end(),
                )

    return None


def find_body_article_positions(
    lines: list[str],
    toc_articles: list[
        dict[str, Any]
    ],
    *,
    body_start: int,
    body_end: int,
) -> tuple[
    list[dict[str, Any]],
    list[str],
]:
    """
    Locate physical Article headings in the
    constitutional body using the canonical
    TOC Article sequence.

    IMPORTANT:

    Omitted Articles are ALSO searched for.

    If an omitted Article physically appears
    in the PDF body, its position is retained
    as a boundary marker so that the preceding
    active Article cannot absorb its text.

    If an omitted Article does NOT physically
    appear in the body, that is acceptable and
    it is not reported as missing.
    """

    positions: list[
        dict[str, Any]
    ] = []

    missing: list[str] = []

    cursor_line = body_start
    cursor_column = 0

    for metadata in toc_articles:
        article_number = (
            metadata[
                "article_number"
            ]
        )

        is_omitted = metadata.get(
            "is_omitted",
            False,
        )

        # -------------------------------------------------
        # Search for BOTH active and omitted Articles.
        #
        # Omitted Articles may still have a physical
        # heading in the body, e.g. Article 2A.
        #
        # Their location is important as a boundary
        # even though we do not want them represented
        # as substantive body Articles later.
        # -------------------------------------------------

        position = (
            find_expected_article_position(
                lines,
                article_number,
                start_line=cursor_line,
                start_column=cursor_column,
                end_line=body_end,
            )
        )

        # -------------------------------------------------
        # Not found
        # -------------------------------------------------

        if position is None:

            # An officially omitted Article may have
            # no physical body heading at all.
            #
            # Example:
            # Article 238 may be represented only by
            # omission metadata / structural text.
            #
            # That is valid and must not fail parsing.
            if is_omitted:
                continue

            # Active Articles MUST exist physically.
            missing.append(
                article_number
            )

            continue

        (
            line_index,
            start_column,
            match_end,
        ) = position

        positions.append(
            {
                **metadata,

                "line_index":
                    line_index,

                "column":
                    start_column,

                "match_end":
                    match_end,

                "source_line":
                    line_index + 1,

                # Omitted positions can be used
                # purely as body boundaries.
                "boundary_only":
                    is_omitted,
            }
        )

        # Advance the ordered search cursor.
        cursor_line = line_index
        cursor_column = match_end

    return (
        positions,
        missing,
    )


def locate_real_article_395(
    lines: list[str],
    *,
    start: int,
) -> int:

    pattern = re.compile(
        r"(?<![A-Za-z0-9])"
        r"(?:\d+\[)*"
        r"\[?\s*"
        r"395\s*\."
        r"\s*Repeals\b",
        re.IGNORECASE,
    )

    for index in range(
        start,
        len(lines),
    ):
        if pattern.search(
            lines[index]
        ):
            return index

    raise RuntimeError(
        "Could not locate real "
        "Article 395 — Repeals."
    )


def schedule_heading_pattern(
    schedule_name: str,
) -> re.Pattern[str]:

    return re.compile(
        rf"^[^A-Za-z0-9]*"
        rf"(?:\d+\[)*"
        rf"\[?\s*"
        rf"(?:THE\s+)?"
        rf"{re.escape(schedule_name)}"
        rf"\s+SCHEDULE\b",
        re.IGNORECASE,
    )


def is_schedule_heading(
    line: str,
    schedule_name: str,
) -> bool:

    match = (
        schedule_heading_pattern(
            schedule_name
        )
        .match(line)
    )

    if not match:
        return False

    suffix = (
        line[
            match.end():
        ]
        .strip()
    )

    # Prevent ordinary sentences like:
    #
    # "Second Schedule to the Constitution..."
    #
    # from being mistaken for a heading.
    if not suffix:
        return True

    return suffix[0] in (
        "[",
        "(",
        "—",
        "–",
        "⎯",
        "-",
    )


def locate_main_first_schedule(
    lines: list[str],
    *,
    article_395_line: int,
) -> int:

    for index in range(
        article_395_line + 1,
        len(lines),
    ):
        if is_schedule_heading(
            lines[index],
            "FIRST",
        ):
            return index

    raise RuntimeError(
        "Could not locate the main "
        "First Schedule after Article 395."
    )


def appendix_heading_pattern() -> re.Pattern[str]:

    return re.compile(
        r"^[^A-Za-z0-9]*"
        r"(?:\d+\[)*"
        r"\[?\s*"
        r"APPENDIX\s+I\b",
        re.IGNORECASE,
    )


def locate_appendix_start(
    lines: list[str],
    *,
    start: int,
) -> int:

    pattern = (
        appendix_heading_pattern()
    )

    for index in range(
        start,
        len(lines),
    ):
        if pattern.match(
            lines[index]
        ):
            return index

    return len(lines)


def second_schedule_anchor_at(
    lines: list[str],
    index: int,
) -> bool:
    """
    The text layer of this official PDF may
    omit the visible SECOND SCHEDULE heading.

    The Article-reference line immediately
    beneath it is stable enough to act as a
    fallback boundary.
    """

    combined = " ".join(
        lines[
            index:
            min(
                len(lines),
                index + 3,
            )
        ]
    )

    normalized = (
        combined
        .upper()
        .replace(" ", "")
    )

    return (
        "ARTICLES59(3)"
        in normalized

        and "65(3)"
        in normalized

        and "75(6)"
        in normalized

        and "148(3)"
        in normalized

        and "158(3)"
        in normalized

        and "221"
        in normalized
    )


def find_schedule_positions(
    lines: list[str],
    *,
    first_schedule_start: int,
    appendix_start: int,
) -> list[
    dict[str, Any]
]:

    positions: list[
        dict[str, Any]
    ] = []

    cursor = (
        first_schedule_start
    )

    for (
        schedule_number,
        schedule_name,
    ) in enumerate(
        SCHEDULE_NAMES,
        start=1,
    ):

        found_index = None

        inferred_from_anchor = (
            False
        )

        if schedule_number == 1:
            found_index = (
                first_schedule_start
            )

        else:
            for index in range(
                cursor + 1,
                appendix_start,
            ):
                if is_schedule_heading(
                    lines[index],
                    schedule_name,
                ):
                    found_index = index
                    break

            # Known extraction-layer
            # fallback for SECOND SCHEDULE.
            if (
                found_index is None
                and schedule_name
                == "SECOND"
            ):
                for index in range(
                    cursor + 1,
                    appendix_start,
                ):
                    if (
                        second_schedule_anchor_at(
                            lines,
                            index,
                        )
                    ):
                        found_index = index

                        inferred_from_anchor = (
                            True
                        )

                        break

        if found_index is None:
            raise RuntimeError(
                "Could not locate "
                f"{schedule_name} SCHEDULE "
                "inside the main "
                "Schedules section."
            )

        positions.append(
            {
                "schedule_number":
                    schedule_number,

                "schedule_name":
                    schedule_name,

                "line_index":
                    found_index,

                "source_line":
                    found_index + 1,

                "inferred_from_anchor":
                    inferred_from_anchor,
            }
        )

        cursor = found_index

    return positions


def slice_text_between(
    lines: list[str],
    *,
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
) -> list[str]:

    if start_line == end_line:
        return [
            lines[start_line][
                start_column:
                end_column
            ].strip()
        ]

    pieces = [
        lines[start_line][
            start_column:
        ].strip()
    ]

    for line_index in range(
        start_line + 1,
        end_line,
    ):
        pieces.append(
            lines[line_index]
        )

    if end_column > 0:
        pieces.append(
            lines[end_line][
                :end_column
            ].strip()
        )

    return pieces


def clean_article_lines(
    raw_lines: list[str],
) -> list[str]:

    cleaned: list[str] = []

    for line in raw_lines:
        if (
            not line
            or is_page_marker(line)
        ):
            continue

        if (
            line
            == "THE CONSTITUTION OF INDIA"
        ):
            continue

        if re.fullmatch(
            r"\(Part .+\)",
            line,
            re.IGNORECASE,
        ):
            continue

        cleaned.append(line)

    # Remove a structural heading accidentally
    # captured immediately before the next
    # Article on a merged line.
    while (
        cleaned
        and is_upper_heading_text(
            cleaned[-1]
        )
    ):
        candidate = cleaned[-1]

        if (
            PART_TOKEN_PATTERN
            .search(candidate)
            or
            CHAPTER_TOKEN_PATTERN
            .search(candidate)
            or
            len(candidate) <= 80
        ):
            cleaned.pop()
            continue

        break

    return cleaned


def split_article_title_and_body(
    article_number: str,
    raw_text: str,
) -> tuple[str, str]:

    pattern = (
        article_heading_regex(
            article_number
        )
    )

    match = pattern.search(
        raw_text
    )

    if not match:
        return (
            "",
            raw_text.strip(),
        )

    content = (
        raw_text[
            match.end():
        ]
        .strip()
    )

    title_match = re.match(
        r"^(?P<title>.*?)"
        r"(?:"
        r"\.\s*[—–⎯-]\s*"
        r"|"
        r"\s+[—–⎯]\s*"
        r")"
        r"(?P<body>.*)$",
        content,
    )

    if title_match:
        title = (
            title_match
            .group("title")
            .strip(" []")
        )

        body = (
            title_match
            .group("body")
            .strip()
        )

        return (
            title,
            body,
        )

    if (
        "OMITTED"
        in content.upper()
    ):
        return (
            "Omitted",
            content,
        )

    # Never invent a title when the PDF
    # extraction damaged the separator.
    return (
        "",
        content,
    )


def build_articles(
    lines: list[str],
    positions: list[
        dict[str, Any]
    ],
    *,
    body_end_line: int,
) -> list[
    dict[str, Any]
]:
    """
    Build substantive Article records from
    physical body positions.

    Omitted Article positions may exist inside
    `positions`, but they are retained only as
    boundary markers.

    Their final structured records are created
    later from authoritative TOC metadata by
    merge_omitted_articles().
    """

    articles: list[
        dict[str, Any]
    ] = []

    for index, position in enumerate(
        positions
    ):

        # -------------------------------------------------
        # Determine boundary FIRST.
        #
        # This deliberately happens before skipping
        # omitted positions conceptually: an omitted
        # Article appearing as positions[index + 1]
        # must terminate the current active Article.
        # -------------------------------------------------

        if (
            index + 1
            < len(positions)
        ):
            next_position = (
                positions[
                    index + 1
                ]
            )

            end_line = (
                next_position[
                    "line_index"
                ]
            )

            end_column = (
                next_position[
                    "column"
                ]
            )

        else:
            end_line = (
                body_end_line
            )

            end_column = 0

        # -------------------------------------------------
        # Omitted Articles are boundary markers only.
        #
        # Do NOT parse their physical body text into
        # substantive Article records.
        #
        # merge_omitted_articles() will later create
        # the canonical omitted record using TOC
        # metadata.
        # -------------------------------------------------

        if position.get(
            "is_omitted",
            False,
        ):
            continue

        raw_lines = (
            slice_text_between(
                lines,

                start_line=
                    position[
                        "line_index"
                    ],

                start_column=
                    position[
                        "column"
                    ],

                end_line=
                    end_line,

                end_column=
                    end_column,
            )
        )

        article_lines = (
            clean_article_lines(
                raw_lines
            )
        )

        raw_text = " ".join(
            article_lines
        ).strip()

        (
            title,
            body,
        ) = (
            split_article_title_and_body(
                position[
                    "article_number"
                ],
                raw_text,
            )
        )

        # -------------------------------------------------
        # Active Articles must have substantive text.
        # -------------------------------------------------

        if not raw_text:
            raise RuntimeError(
                "Active Article produced "
                "empty raw text: "
                f"{position['article_number']}"
            )

        articles.append(
            {
                "article_number":
                    position[
                        "article_number"
                    ],

                "part":
                    position.get(
                        "part"
                    ),

                "part_title":
                    position.get(
                        "part_title",
                        "",
                    ),

                "title":
                    title,

                "text":
                    body,

                "raw_text":
                    raw_text,

                "is_omitted":
                    False,

                "source_line":
                    position.get(
                        "source_line"
                    ),

                "toc_source_line":
                    position.get(
                        "toc_source_line"
                    ),
            }
        )

    return articles


def build_schedules(
    lines: list[str],
    positions: list[
        dict[str, Any]
    ],
    *,
    appendix_start: int,
) -> list[
    dict[str, Any]
]:

    schedules: list[
        dict[str, Any]
    ] = []

    for index, position in enumerate(
        positions
    ):

        if (
            index + 1
            < len(positions)
        ):
            end_line = (
                positions[
                    index + 1
                ][
                    "line_index"
                ]
            )

        else:
            end_line = (
                appendix_start
            )

        raw_lines = [
            line
            for line
            in lines[
                position[
                    "line_index"
                ]:
                end_line
            ]
            if (
                line
                and not is_page_marker(
                    line
                )
            )
        ]

        schedules.append(
            {
                "schedule_number":
                    position[
                        "schedule_number"
                    ],

                "schedule_name":
                    position[
                        "schedule_name"
                    ],

                "source_line":
                    position[
                        "source_line"
                    ],

                "boundary_inferred_from_anchor":
                    position[
                        "inferred_from_anchor"
                    ],

                "raw_text":
                    " ".join(
                        raw_lines
                    ).strip(),
            }
        )

    return schedules


def build_parts(
    toc_articles: list[
        dict[str, Any]
    ],
    part_titles: dict[
        str,
        str,
    ],
) -> list[
    dict[str, Any]
]:

    parts: list[
        dict[str, Any]
    ] = []

    seen: set[str] = set()

    for article in toc_articles:
        part_number = (
            article.get("part")
        )

        if (
            not part_number
            or part_number in seen
        ):
            continue

        seen.add(
            part_number
        )

        parts.append(
            {
                "number":
                    part_number,

                "title":
                    part_titles.get(
                        part_number,
                        "",
                    ),
            }
        )

    return parts

def omitted_article_title(
    article: dict[str, Any],
) -> str:
    raw_text = article.get(
        "toc_raw_text",
        "",
    )

    article_number = article[
        "article_number"
    ]

    pattern = article_heading_regex(
        article_number
    )

    match = pattern.search(
        raw_text
    )

    if match:
        title_text = raw_text[
            match.end():
        ]
    else:
        title_text = raw_text

    # Stop at the word "Omitted".
    #
    # Anything after that may belong to
    # the next structural heading such as:
    #
    # PART VIII
    # RIGHT TO CONSTITUTIONAL REMEDIES
    # CHAPTER II
    #
    # and must not become part of the
    # Article title.
    title_text = re.split(
        r"\bOMITTED\b",
        title_text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    return (
        title_text
        .strip()
        .strip(
            "[] .—–⎯-"
        )
    )


def merge_omitted_articles(
    toc_articles: list[
        dict[str, Any]
    ],
    body_articles: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    """
    Return the complete constitutional Article
    index in official TOC order.

    Substantive Articles come from the body.
    Officially omitted Articles are represented
    as metadata-only records.
    """

    body_map = {
        article[
            "article_number"
        ]:
        article
        for article
        in body_articles
    }

    result: list[
        dict[str, Any]
    ] = []

    for metadata in toc_articles:
        number = (
            metadata[
                "article_number"
            ]
        )

        if metadata.get(
            "is_omitted",
            False,
        ):
            result.append(
                {
                    "article_number":
                        number,

                    "part":
                        metadata.get(
                            "part"
                        ),

                    "part_title":
                        metadata.get(
                            "part_title",
                            "",
                        ),

                    "title":
                        omitted_article_title(
                            metadata
                        ),

                    "text":
                        "",

                    "raw_text":
                        metadata.get(
                            "toc_raw_text",
                            "",
                        ),

                    "is_omitted":
                        True,

                    "source_line":
                        None,

                    "toc_source_line":
                        metadata.get(
                            "toc_source_line"
                        ),
                }
            )

            continue

        article = body_map.get(
            number
        )

        if article is not None:
            result.append(
                article
            )

    return result


def validate_parsed_data(
    *,
    preamble: str,
    toc_articles: list[
        dict[str, Any]
    ],
    body_articles: list[
        dict[str, Any]
    ],
    missing_body_articles: list[str],
    schedules: list[
        dict[str, Any]
    ],
) -> None:

    if (
        "WE, THE PEOPLE OF INDIA"
        not in preamble
    ):
        raise RuntimeError(
            "Preamble validation failed."
        )

    expected_numbers = [
        item[
            "article_number"
        ]
        for item in toc_articles
    ]

    parsed_numbers = [
        item[
            "article_number"
        ]
        for item in body_articles
    ]

    if missing_body_articles:
        raise RuntimeError(
            "Some Articles listed in "
            "the official Contents "
            "could not be matched in "
            "the constitutional body: "
            + ", ".join(
                missing_body_articles[
                    :30
                ]
            )
        )

    if (
        parsed_numbers
        != expected_numbers
    ):
        mismatch_index = next(
            (
                index
                for (
                    index,
                    (
                        expected,
                        parsed,
                    ),
                )
                in enumerate(
                    zip(
                        expected_numbers,
                        parsed_numbers,
                    )
                )
                if (
                    expected
                    != parsed
                )
            ),
            None,
        )

        raise RuntimeError(
            "Body Article sequence does "
            "not exactly match the "
            "official Contents index. "
            "First mismatch index: "
            f"{mismatch_index}"
        )

    if (
        parsed_numbers[0]
        != "1"
        or
        parsed_numbers[-1]
        != "395"
    ):
        raise RuntimeError(
            "Article boundary validation "
            "failed: expected Article 1 "
            "through Article 395."
        )

    duplicates = sorted(
        {
            number
            for number
            in parsed_numbers
            if (
                parsed_numbers.count(
                    number
                )
                > 1
            )
        }
    )

    if duplicates:
        raise RuntimeError(
            "Duplicate Article "
            "identifiers detected: "
            + ", ".join(
                duplicates
            )
        )

    missing_required = sorted(
        REQUIRED_ARTICLES
        - set(parsed_numbers)
    )

    if missing_required:
        raise RuntimeError(
            "Required Article "
            "identifiers missing: "
            + ", ".join(
                missing_required
            )
        )

    schedule_names = [
        schedule[
            "schedule_name"
        ]
        for schedule
        in schedules
    ]

    if (
        schedule_names
        != SCHEDULE_NAMES
    ):
        raise RuntimeError(
            "Schedule sequence "
            "validation failed. "
            f"Detected: "
            f"{schedule_names}"
        )

    article_map = {
        article[
            "article_number"
        ]:
        article
        for article
        in body_articles
    }

    semantic_checks = {
        "21":
            "personal liberty",

        "32":
            "remedies",

        "226":
            "High Courts",

        "368":
            "amend",

        "370":
            "Jammu and Kashmir",

        "395":
            "Indian Independence Act",
    }

    for (
        article_number,
        expected_phrase,
    ) in semantic_checks.items():

        article_text = (
            article_map[
                article_number
            ][
                "raw_text"
            ]
        )

        if (
            expected_phrase.lower()
            not in article_text.lower()
        ):
            raise RuntimeError(
                f"Article "
                f"{article_number} "
                "semantic validation "
                "failed; expected "
                "phrase not found: "
                f"{expected_phrase!r}"
            )

        article_map = {
        article[
            "article_number"
        ]:
        article
        for article
        in body_articles
    }

    # Article 237 is operative.
    # PART VII following it is omitted,
    # not Article 237 itself.
    if article_map[
        "237"
    ][
        "is_omitted"
    ]:
        raise RuntimeError(
            "Article 237 was incorrectly "
            "classified as omitted."
        )

    # Article 238 is an omitted provision.
    if not article_map[
        "238"
    ][
        "is_omitted"
    ]:
        raise RuntimeError(
            "Article 238 should be "
            "classified as omitted."
        )


def print_article_sample(
    article_map: dict[
        str,
        dict[str, Any],
    ],
    article_number: str,
) -> None:

    article = article_map.get(
        article_number
    )

    if article is None:
        print(
            f"\nArticle "
            f"{article_number}: "
            "NOT FOUND"
        )
        return

    preview = (
        article["text"][
            :220
        ]
        .replace(
            "\n",
            " ",
        )
    )

    print(
        f"\nArticle "
        f"{article_number}"
    )

    print(
        f"Part: "
        f"{article['part']}"
    )

    print(
        "Part title: "
        f"{article['part_title']}"
    )

    print(
        f"Title: "
        f"{article['title']}"
    )

    print(
        f"Omitted: "
        f"{article['is_omitted']}"
    )

    print(
        f"Text preview: "
        f"{preview}"
    )


def parse_constitution() -> None:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "Extracted Constitution "
            "text not found: "
            f"{INPUT_FILE}"
        )

    if not SOURCE_PDF.exists():
        raise FileNotFoundError(
            "Constitution source "
            "PDF not found: "
            f"{SOURCE_PDF}"
        )

    print(
        "Verifying locked "
        "Constitution source..."
    )

    actual_hash = (
        calculate_sha256(
            SOURCE_PDF
        )
    )

    print(
        f"PDF SHA-256: "
        f"{actual_hash}"
    )

    if (
        actual_hash
        != EXPECTED_PDF_SHA256
    ):
        raise RuntimeError(
            "Constitution PDF hash "
            "does not match the "
            "locked canonical source."
        )

    print(
        "Locked source hash "
        "verified."
    )

    raw_text = (
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    lines = [
        clean_line(line)
        for line
        in raw_text.splitlines()
    ]

    (
        preamble_start,
        preamble_end,
    ) = locate_preamble(
        lines
    )

    actual_part_one = (
        locate_actual_part_one(
            lines,
            preamble_end,
        )
    )

    contents_index = (
        locate_first_exact(
            lines,
            "CONTENTS",
            start=0,
            end=preamble_start,
        )
    )

    toc_schedules_index = (
        locate_first_exact(
            lines,
            "SCHEDULES",
            start=
                contents_index + 1,
            end=preamble_start,
        )
    )

    (
        toc_articles,
        part_titles,
    ) = (
        parse_toc_article_index(
            lines,
            contents_index,
            toc_schedules_index,
        )
    )

    article_395_line = (
        locate_real_article_395(
            lines,
            start=actual_part_one,
        )
    )

    first_schedule_start = (
        locate_main_first_schedule(
            lines,
            article_395_line=
                article_395_line,
        )
    )

    appendix_start = (
        locate_appendix_start(
            lines,
            start=
                first_schedule_start
                + 1,
        )
    )

    (
        positions,
        missing_body_articles,
    ) = (
        find_body_article_positions(
            lines,
            toc_articles,

            body_start=
                actual_part_one,

            body_end=
                first_schedule_start,
        )
    )

    body_articles = build_articles(
    lines,
    positions,
    body_end_line=
        first_schedule_start,
)

    articles = merge_omitted_articles(
        toc_articles,
        body_articles,
)

    schedule_positions = (
        find_schedule_positions(
            lines,

            first_schedule_start=
                first_schedule_start,

            appendix_start=
                appendix_start,
        )
    )

    schedules = (
        build_schedules(
            lines,
            schedule_positions,
            appendix_start=
                appendix_start,
        )
    )

    preamble = " ".join(
        line
        for line
        in lines[
            preamble_start + 1:
            preamble_end + 1
        ]
        if (
            line
            and not is_page_marker(
                line
            )
        )
    ).strip()

    print(
        "\nPre-validation "
        "diagnostics:"
    )

    print(
        "TOC Articles expected: "
        f"{len(toc_articles)}"
    )

    print(
    "Body Articles matched: "
    f"{len(body_articles)}"
)

    print(
    "Final Article records: "
    f"{len(articles)}"
)

    if articles:
        print(
            "First parsed Article: "
            f"{articles[0]['article_number']}"
        )

        print(
            "Last parsed Article: "
            f"{articles[-1]['article_number']}"
        )

    print(
        "Missing body Articles: "
        f"{len(missing_body_articles)}"
    )

    if missing_body_articles:
        print(
            "Missing IDs: "
            + ", ".join(
                missing_body_articles[
                    :30
                ]
            )
        )

    print(
        "Schedules parsed: "
        f"{len(schedules)}"
    )

    print(
        "Schedule boundaries: "
        + ", ".join(
            (
                f"{item['schedule_name']}"
                f"@{item['source_line']}"
                + (
                    " [anchor]"
                    if item[
                        "inferred_from_anchor"
                    ]
                    else ""
                )
            )
            for item
            in schedule_positions
        )
    )

    validate_parsed_data(
    preamble=preamble,

    toc_articles=
        toc_articles,

    body_articles=
        articles,

    missing_body_articles=
        missing_body_articles,

    schedules=
        schedules,
)

    parts = build_parts(
        toc_articles,
        part_titles,
    )

    output = {
        "metadata": {
            "title":
                "The Constitution "
                "of India",

            "edition_as_on":
                "1 May 2026",

            "language":
                "en",

            "publisher":
                (
                    "Legislative Department, "
                    "Ministry of Law and Justice, "
                    "Government of India"
                ),

            "source_pdf":
                SOURCE_PDF.name,

            "source_pdf_size_bytes":
                SOURCE_PDF
                .stat()
                .st_size,

            "source_pdf_sha256":
                actual_hash,

            "toc_article_count":
                len(
                    toc_articles
                ),

            "parsed_article_count":
                len(
                    articles
                ),

            "part_count":
                len(
                    parts
                ),

            "schedule_count":
                len(
                    schedules
                ),

            "appendices_included_in_article_corpus":
                False,
        },

        "preamble":
            preamble,

        "parts":
            parts,

        "articles":
            articles,

        "schedules":
            schedules,
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    article_map = {
        article[
            "article_number"
        ]:
        article

        for article
        in articles
    }

    print(
        "\nConstitution parsing "
        "completed."
    )

    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Parts detected: "
        f"{len(parts)}"
    )

    print(
        "Articles detected: "
        f"{len(articles)}"
    )

    print(
        "Schedules detected: "
        f"{len(schedules)}"
    )

    print(
        "\nBoundary positions:"
    )

    print(
        "Preamble source line: "
        f"{preamble_start + 1}"
    )

    print(
        "PART I source line: "
        f"{actual_part_one + 1}"
    )

    print(
        "Article 395 "
        "source line: "
        f"{article_395_line + 1}"
    )

    print(
        "First Schedule "
        "source line: "
        f"{first_schedule_start + 1}"
    )

    print(
        "Appendix I "
        "source line: "
        f"{appendix_start + 1}"
    )

    for article_number in (
        SAMPLE_ARTICLES
    ):
        print_article_sample(
            article_map,
            article_number,
        )

    print(
        "\nVALIDATION PASSED ✅"
    )


if __name__ == "__main__":
    parse_constitution()
