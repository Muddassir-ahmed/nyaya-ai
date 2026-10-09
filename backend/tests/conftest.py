import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.engine import make_url

from app.core.config import settings


# ---------------------------------------------------------
# TEST DATABASE SAFETY GATE
# ---------------------------------------------------------

if not settings.TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured. "
        "Pytest will not run against the normal database."
    )

test_url = make_url(settings.TEST_DATABASE_URL)

if test_url.database != "nyaya_test":
    raise RuntimeError(
        "Refusing to run tests because TEST_DATABASE_URL "
        "does not point to the 'nyaya_test' database."
    )

if settings.TEST_DATABASE_URL == settings.DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must not be the same as DATABASE_URL."
    )


# Override the settings object BEFORE app.db.session is imported.
# This makes the app's engine/session point to nyaya_test
# for the entire pytest process.
settings.DATABASE_URL = settings.TEST_DATABASE_URL


from app.db.session import AsyncSessionLocal, engine
from app.models.authority import Authority
from app.models.emergency_contact import EmergencyContact
from app.models.jurisdiction import Jurisdiction


async def _cleanup_test_data(session):
    """
    Remove only data created by automated tests.

    Authority rows must be deleted before their test
    jurisdictions because of the foreign-key constraint.
    """

    # Authority tests currently create only synthetic records.
    await session.execute(
        delete(Authority).where(
            Authority.name.like("Test %")
            | Authority.name.in_(
                [
                    "Unverified Authority",
                    "Inactive Authority",
                    "Verified Active Authority",
                    "Secondary Authority",
                    "Primary Authority",
                ]
            )
        )
    )

    # Remove only synthetic jurisdictions used by tests.
    await session.execute(
        delete(Jurisdiction).where(
            Jurisdiction.code.like("T-%")
        )
    )

    # Preserve existing emergency-test behavior.
    await session.execute(
        delete(EmergencyContact)
    )

    await session.commit()


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        try:
            # Clean leftovers from an interrupted/previous test run.
            await _cleanup_test_data(session)

            yield session

        finally:
            # A failed flush/commit leaves SQLAlchemy in a failed
            # transaction state. Roll back before attempting cleanup.
            await session.rollback()

            await _cleanup_test_data(session)

            await session.close()
            await engine.dispose()


@pytest_asyncio.fixture
async def verified_112(db_session):
    fallback_112 = EmergencyContact(
        name="Test 112",
        emergency_type="other",
        phone_number="112",
        jurisdiction="India",
        primary_source_name="Test Source",
        primary_source_url="https://example.com",
        is_verified=True,
        is_active=True,
    )

    db_session.add(fallback_112)
    await db_session.commit()

    return fallback_112