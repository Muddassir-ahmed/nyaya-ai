from collections import Counter
from pathlib import Path
import re

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.legal_document import LegalDocument
from app.models.section import Section
from app.models.subsection import Subsection
from app.models.clause import Clause


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PARSED_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "bns_parsed.txt"
)


# =========================================================
# CANONICAL BNS STRUCTURE
# =========================================================

EXPECTED_SECTIONS = 358
EXPECTED_SUBSECTIONS = 310
EXPECTED_CLAUSES = 115
EXPECTED_ILLUSTRATION_LINES = 935


# =========================================================
# PARSED-FILE CONTROL MARKERS
# =========================================================

SECTION_PATTERN = re.compile(
    r"^===== SECTION (\d+) =====$"
)

TITLE_PATTERN = re.compile(
    r"^TITLE:\s*(.*)$"
)

SECTION_TEXT_PATTERN = re.compile(
    r"^SECTION TEXT:$"
)

SUBSECTION_PATTERN = re.compile(
    r"^--- SUBSECTION \((\d+)\) ---$"
)

CLAUSE_PATTERN = re.compile(
    r"^CLAUSE \(([a-z]+)\):$"
)

ILLUSTRATIONS_PATTERN = re.compile(
    r"^ILLUSTRATIONS:$"
)

SECTION_SUPPLEMENTARY_PATTERN = re.compile(
    r"^SECTION SUPPLEMENTARY:$"
)

SUBSECTION_SUPPLEMENTARY_PATTERN = re.compile(
    r"^SUBSECTION SUPPLEMENTARY:$"
)


# =========================================================
# DATABASE LOOKUP
# =========================================================

async def get_bns_document(db):
    result = await db.execute(
        select(LegalDocument)
        .where(
            LegalDocument.title
            == "The Bharatiya Nyaya Sanhita, 2023"
        )
    )

    document = result.scalar_one_or_none()

    if document is None:
        raise RuntimeError(
            "BNS legal document not found."
        )

    return document


# =========================================================
# PARSE bns_parsed.txt
# =========================================================

def parse_sections(
    parsed_file: Path = PARSED_FILE,
):
    """
    Parse bns_parsed.txt into the hierarchy used for
    database ingestion.

    Important rules:

    - SECTION TEXT: is a control marker only.
    - ILLUSTRATIONS: is a control marker only.
    - SECTION SUPPLEMENTARY: is a control marker only.
    - SUBSECTION SUPPLEMENTARY: is a control marker only.

    - Illustration lines never become Clause rows.
    - Supplementary numbered items never become
      Clause rows.

    - Section-level illustrations belong to Section.
    - Subsection-level illustrations belong to
      Subsection.

    - Section supplementary material belongs to Section.
    - Subsection supplementary material belongs to
      Subsection.
    """

    text = parsed_file.read_text(
        encoding="utf-8"
    )

    lines = text.splitlines()

    sections = []

    current_section = None
    current_subsection = None
    current_clause = None

    in_illustrations = False

    # Direct reference to either:
    #
    # section["supplementary"]
    #
    # or:
    #
    # subsection["supplementary"]
    #
    # while a supplementary block is active.
    supplementary_owner = None

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        # =================================================
        # SECTION
        # =================================================

        section_match = SECTION_PATTERN.match(
            line
        )

        if section_match:

            current_section = {
                "number": (
                    section_match.group(1)
                ),
                "title": "",
                "text": [],
                "illustrations": [],
                "supplementary": [],
                "subsections": [],
            }

            sections.append(
                current_section
            )

            current_subsection = None
            current_clause = None

            in_illustrations = False
            supplementary_owner = None

            continue

        if current_section is None:
            continue

        # =================================================
        # TITLE
        # =================================================

        title_match = TITLE_PATTERN.match(
            line
        )

        if title_match:

            current_section["title"] = (
                title_match
                .group(1)
                .strip()
            )

            continue

        # =================================================
        # SECTION TEXT MARKER
        # =================================================

        if SECTION_TEXT_PATTERN.match(
            line
        ):

            current_clause = None

            in_illustrations = False
            supplementary_owner = None

            continue

        # =================================================
        # SUBSECTION
        # =================================================

        subsection_match = (
            SUBSECTION_PATTERN.match(
                line
            )
        )

        if subsection_match:

            current_subsection = {
                "number": (
                    f"("
                    f"{subsection_match.group(1)}"
                    f")"
                ),
                "text": [],
                "illustrations": [],
                "supplementary": [],
                "clauses": [],
            }

            current_section[
                "subsections"
            ].append(
                current_subsection
            )

            current_clause = None

            in_illustrations = False
            supplementary_owner = None

            continue

        # =================================================
        # SECTION SUPPLEMENTARY MARKER
        # =================================================
        #
        # Example:
        #
        # SECTION SUPPLEMENTARY:
        # Exception.—This section does not extend to—
        # (a) ...
        #     (i) ...
        #
        # All following lines belong to the Section until
        # the next structural boundary.

        if SECTION_SUPPLEMENTARY_PATTERN.match(
            line
        ):

            current_clause = None

            in_illustrations = False

            supplementary_owner = (
                current_section[
                    "supplementary"
                ]
            )

            continue

        # =================================================
        # SUBSECTION SUPPLEMENTARY MARKER
        # =================================================

        if SUBSECTION_SUPPLEMENTARY_PATTERN.match(
            line
        ):

            if current_subsection is None:
                raise RuntimeError(
                    "SUBSECTION SUPPLEMENTARY "
                    "encountered without an active "
                    "subsection."
                )

            current_clause = None

            in_illustrations = False

            supplementary_owner = (
                current_subsection[
                    "supplementary"
                ]
            )

            continue

        # =================================================
        # ILLUSTRATIONS MARKER
        # =================================================

        if ILLUSTRATIONS_PATTERN.match(
            line
        ):

            current_clause = None

            in_illustrations = True
            supplementary_owner = None

            continue

        # =================================================
        # SUPPLEMENTARY CONTENT
        # =================================================
        #
        # This MUST occur before Clause parsing.
        #
        # Supplementary material frequently contains:
        #
        #     (a)
        #     (b)
        #     (i)
        #     (ii)
        #
        # Those are nested statutory material, NOT Clause
        # database rows.

        if supplementary_owner is not None:

            supplementary_owner.append(
                line
            )

            continue

        # =================================================
        # ILLUSTRATION CONTENT
        # =================================================
        #
        # This must also occur before Clause parsing because
        # illustrations often begin with (a), (b), etc.

        if in_illustrations:

            if current_subsection is not None:

                current_subsection[
                    "illustrations"
                ].append(
                    line
                )

            else:

                current_section[
                    "illustrations"
                ].append(
                    line
                )

            continue

        # =================================================
        # CLAUSE
        # =================================================

        clause_match = CLAUSE_PATTERN.match(
            line
        )

        if (
            clause_match
            and current_subsection is not None
        ):

            current_clause = {
                "number": (
                    f"("
                    f"{clause_match.group(1)}"
                    f")"
                ),
                "text": [],
            }

            current_subsection[
                "clauses"
            ].append(
                current_clause
            )

            continue

        # =================================================
        # NORMAL CONTENT
        # =================================================

        if current_clause is not None:

            current_clause[
                "text"
            ].append(
                line
            )

        elif current_subsection is not None:

            current_subsection[
                "text"
            ].append(
                line
            )

        else:

            current_section[
                "text"
            ].append(
                line
            )

    return sections


# =========================================================
# BUILD DATABASE PARENT TEXT
# =========================================================

def build_parent_text(
    text_lines,
    illustration_lines,
    supplementary_lines=None,
):
    """
    Build Section/Subsection text for database storage.

    Ordinary statutory text, illustrations and
    supplementary provisions are preserved separately
    before being combined.

    Supplementary material keeps its original statutory
    wording such as:

        Explanation.—
        Exception.—
        Provided that...

    No synthetic legal wording is added.
    """

    if supplementary_lines is None:
        supplementary_lines = []

    body = " ".join(
        text_lines
    ).strip()

    illustrations = " ".join(
        illustration_lines
    ).strip()

    supplementary = " ".join(
        supplementary_lines
    ).strip()

    parts = []

    if body:
        parts.append(
            body
        )

    if illustrations:
        parts.append(
            "Illustrations.\n"
            f"{illustrations}"
        )

    if supplementary:
        parts.append(
            supplementary
        )

    return "\n\n".join(
        parts
    )


# =========================================================
# STRUCTURE STATISTICS
# =========================================================

def get_structure_stats(
    sections,
):
    subsection_total = sum(
        len(
            section["subsections"]
        )
        for section in sections
    )

    clause_total = sum(
        len(
            subsection["clauses"]
        )
        for section in sections
        for subsection
        in section["subsections"]
    )

    illustration_line_total = sum(
        len(
            section["illustrations"]
        )
        + sum(
            len(
                subsection[
                    "illustrations"
                ]
            )
            for subsection
            in section["subsections"]
        )
        for section in sections
    )

    supplementary_line_total = sum(
        len(
            section["supplementary"]
        )
        + sum(
            len(
                subsection[
                    "supplementary"
                ]
            )
            for subsection
            in section["subsections"]
        )
        for section in sections
    )

    return {
        "sections": len(
            sections
        ),
        "subsections": (
            subsection_total
        ),
        "clauses": (
            clause_total
        ),
        "illustrations": (
            illustration_line_total
        ),
        "supplementary": (
            supplementary_line_total
        ),
    }


# =========================================================
# SECTION VALIDATION
# =========================================================

def validate_sections_for_ingestion(
    sections,
):
    """
    Refuse ingestion unless the parsed BNS contains
    exactly one copy of every Section from 1 through 358.

    This function keeps the original section-level
    invariant.

    Full canonical subordinate-count validation is
    performed separately by
    validate_canonical_bns_structure().
    """

    section_numbers = [
        int(
            section["number"]
        )
        for section in sections
    ]

    counts = Counter(
        section_numbers
    )

    duplicates = sorted(
        number
        for number, count
        in counts.items()
        if count > 1
    )

    expected = set(
        range(
            1,
            EXPECTED_SECTIONS + 1,
        )
    )

    actual = set(
        section_numbers
    )

    missing = sorted(
        expected - actual
    )

    outside = sorted(
        actual - expected
    )

    errors = []

    if (
        len(section_numbers)
        != EXPECTED_SECTIONS
    ):

        errors.append(
            "Expected "
            f"{EXPECTED_SECTIONS} "
            "section records, "
            f"found "
            f"{len(section_numbers)}."
        )

    if duplicates:

        errors.append(
            "Duplicate sections: "
            + ", ".join(
                str(number)
                for number
                in duplicates
            )
        )

    if missing:

        errors.append(
            "Missing sections: "
            + ", ".join(
                str(number)
                for number
                in missing
            )
        )

    if outside:

        errors.append(
            "Out-of-range sections: "
            + ", ".join(
                str(number)
                for number
                in outside
            )
        )

    if errors:

        raise RuntimeError(
            "BNS structural validation "
            "failed:\n"
            + "\n".join(
                errors
            )
        )


# =========================================================
# FULL CANONICAL VALIDATION
# =========================================================

def validate_canonical_bns_structure(
    sections,
):
    """
    Validate the complete canonical BNS hierarchy
    established from the official source.

    Expected:

        358 Sections
        310 Subsections
        115 top-level Clauses
        935 illustration lines

    Also rejects duplicate subsection and clause keys.
    """

    validate_sections_for_ingestion(
        sections
    )

    stats = get_structure_stats(
        sections
    )

    errors = []

    if (
        stats["subsections"]
        != EXPECTED_SUBSECTIONS
    ):

        errors.append(
            "Expected "
            f"{EXPECTED_SUBSECTIONS} "
            "subsections, found "
            f"{stats['subsections']}."
        )

    if (
        stats["clauses"]
        != EXPECTED_CLAUSES
    ):

        errors.append(
            "Expected "
            f"{EXPECTED_CLAUSES} "
            "clauses, found "
            f"{stats['clauses']}."
        )

    if (
        stats["illustrations"]
        != EXPECTED_ILLUSTRATION_LINES
    ):

        errors.append(
            "Expected "
            f"{EXPECTED_ILLUSTRATION_LINES} "
            "illustration lines, found "
            f"{stats['illustrations']}."
        )

    # -----------------------------------------------------
    # Duplicate subsection keys
    # -----------------------------------------------------

    duplicate_subsections = []

    for section in sections:

        subsection_numbers = [
            subsection["number"]
            for subsection
            in section["subsections"]
        ]

        counts = Counter(
            subsection_numbers
        )

        for number, count in (
            counts.items()
        ):

            if count > 1:

                duplicate_subsections.append(
                    (
                        section["number"],
                        number,
                    )
                )

    if duplicate_subsections:

        errors.append(
            "Duplicate subsection keys: "
            + ", ".join(
                f"Section {section_number} "
                f"{subsection_number}"
                for (
                    section_number,
                    subsection_number,
                )
                in duplicate_subsections
            )
        )

    # -----------------------------------------------------
    # Duplicate clause keys
    # -----------------------------------------------------

    duplicate_clauses = []

    for section in sections:

        for subsection in (
            section["subsections"]
        ):

            clause_numbers = [
                clause["number"]
                for clause
                in subsection["clauses"]
            ]

            counts = Counter(
                clause_numbers
            )

            for number, count in (
                counts.items()
            ):

                if count > 1:

                    duplicate_clauses.append(
                        (
                            section[
                                "number"
                            ],
                            subsection[
                                "number"
                            ],
                            number,
                        )
                    )

    if duplicate_clauses:

        errors.append(
            "Duplicate clause keys: "
            + ", ".join(
                f"Section {section_number} "
                f"{subsection_number} "
                f"{clause_number}"
                for (
                    section_number,
                    subsection_number,
                    clause_number,
                )
                in duplicate_clauses
            )
        )

    if errors:

        raise RuntimeError(
            "Canonical BNS validation "
            "failed:\n"
            + "\n".join(
                errors
            )
        )


# =========================================================
# DATABASE HELPERS
# =========================================================

async def get_or_create_section(
    db,
    version_id,
    number,
    title,
    text,
):

    result = await db.execute(
        select(Section).where(
            Section.version_id
            == version_id,
            Section.section_number
            == number,
        )
    )

    section = (
        result.scalar_one_or_none()
    )

    if section:
        return section

    section = Section(
        version_id=version_id,
        section_number=number,
        title=title,
        text=text,
    )

    db.add(
        section
    )

    await db.flush()

    return section


async def get_or_create_subsection(
    db,
    section_id,
    number,
    text,
):

    result = await db.execute(
        select(Subsection).where(
            Subsection.section_id
            == section_id,
            Subsection.subsection_number
            == number,
        )
    )

    subsection = (
        result.scalar_one_or_none()
    )

    if subsection:
        return subsection

    subsection = Subsection(
        section_id=section_id,
        subsection_number=number,
        text=text,
    )

    db.add(
        subsection
    )

    await db.flush()

    return subsection


async def get_or_create_clause(
    db,
    subsection_id,
    number,
    text,
):

    result = await db.execute(
        select(Clause).where(
            Clause.subsection_id
            == subsection_id,
            Clause.clause_number
            == number,
        )
    )

    clause = (
        result.scalar_one_or_none()
    )

    if clause:
        return clause

    clause = Clause(
        subsection_id=subsection_id,
        clause_number=number,
        text=text,
    )

    db.add(
        clause
    )

    await db.flush()

    return clause


# =========================================================
# INGESTION
# =========================================================

async def ingest_bns():

    if not PARSED_FILE.exists():

        raise FileNotFoundError(
            "Parsed BNS file not found: "
            f"{PARSED_FILE}"
        )

    print(
        "Parsing BNS structure..."
    )

    sections = parse_sections()

    # -----------------------------------------------------
    # HARD VALIDATION
    #
    # Nothing touches PostgreSQL unless the complete
    # canonical BNS structure passes first.
    # -----------------------------------------------------

    validate_canonical_bns_structure(
        sections
    )

    stats = get_structure_stats(
        sections
    )

    print(
        "BNS structural validation "
        "passed."
    )

    print(
        "Sections ready for ingestion: "
        f"{stats['sections']}"
    )

    print(
        "Subsections parsed: "
        f"{stats['subsections']}"
    )

    print(
        "Clauses parsed: "
        f"{stats['clauses']}"
    )

    print(
        "Illustration lines preserved: "
        f"{stats['illustrations']}"
    )

    print(
        "Supplementary lines preserved: "
        f"{stats['supplementary']}"
    )

    # =====================================================
    # DATABASE TRANSACTION
    # =====================================================

    async with AsyncSessionLocal() as db:

        document = await get_bns_document(
            db
        )

        if document.act_id is None:

            raise RuntimeError(
                "BNS document is not linked "
                "to an Act."
            )

        from app.models.legal_version import (
            LegalVersion,
        )

        result = await db.execute(
            select(LegalVersion)
            .where(
                LegalVersion.act_id
                == document.act_id,
                LegalVersion.status
                == "active",
            )
        )

        version = (
            result.scalar_one_or_none()
        )

        if version is None:

            raise RuntimeError(
                "Active BNS legal version "
                "not found."
            )

        section_count = 0
        subsection_count = 0
        clause_count = 0

        for section_data in sections:

            # -------------------------------------------------
            # SECTION TEXT
            # -------------------------------------------------

            section_text = (
                build_parent_text(
                    section_data[
                        "text"
                    ],
                    section_data[
                        "illustrations"
                    ],
                    section_data[
                        "supplementary"
                    ],
                )
            )

            section = (
                await get_or_create_section(
                    db=db,
                    version_id=version.id,
                    number=section_data[
                        "number"
                    ],
                    title=section_data[
                        "title"
                    ],
                    text=section_text,
                )
            )

            section_count += 1

            # =============================================
            # SUBSECTIONS
            # =============================================

            for subsection_data in (
                section_data[
                    "subsections"
                ]
            ):

                subsection_text = (
                    build_parent_text(
                        subsection_data[
                            "text"
                        ],
                        subsection_data[
                            "illustrations"
                        ],
                        subsection_data[
                            "supplementary"
                        ],
                    )
                )

                subsection = (
                    await get_or_create_subsection(
                        db=db,
                        section_id=section.id,
                        number=subsection_data[
                            "number"
                        ],
                        text=subsection_text,
                    )
                )

                subsection_count += 1

                # =========================================
                # CLAUSES
                # =========================================

                for clause_data in (
                    subsection_data[
                        "clauses"
                    ]
                ):

                    clause_text = (
                        " ".join(
                            clause_data[
                                "text"
                            ]
                        )
                        .strip()
                    )

                    await get_or_create_clause(
                        db=db,
                        subsection_id=(
                            subsection.id
                        ),
                        number=clause_data[
                            "number"
                        ],
                        text=clause_text,
                    )

                    clause_count += 1

        await db.commit()

    # =====================================================
    # COMPLETE
    # =====================================================

    print(
        "\nBNS ingestion completed."
    )

    print(
        f"Sections: "
        f"{section_count}"
    )

    print(
        f"Subsections: "
        f"{subsection_count}"
    )

    print(
        f"Clauses: "
        f"{clause_count}"
    )


if __name__ == "__main__":

    import asyncio

    asyncio.run(
        ingest_bns()
    )